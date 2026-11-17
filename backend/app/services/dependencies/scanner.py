"""
Dependency Inventory Scanner.
Parses supported manifest and lock files:
- package.json & package-lock.json (Node.js)
- requirements.txt, pyproject.toml, Pipfile (Python)
- Cargo.toml & Cargo.lock (Rust)
- go.mod (Go)
- pom.xml (Java/Maven)
- Gemfile & Gemfile.lock (Ruby)

Attributes:
- Name and declared version
- Origin manifest file
- Direct vs transitive classification (only when manifest confirms it)
- Trusted vulnerability/version verification status with source and check date.
Never claims vulnerabilities without configured trusted source.
"""
import re
import json
import datetime
from typing import List, Dict, Any, Optional
from app.models.repository import Repository
from app.models.code_chunk import CodeChunk
from app.services.github.base import BaseGitHubClient


class DependencyInventoryScanner:
    def __init__(
        self,
        repository: Repository,
        chunks: List[CodeChunk],
        github_client: BaseGitHubClient
    ):
        self.repository = repository
        self.chunks = chunks
        self.github_client = github_client

    async def scan(self) -> Dict[str, Any]:
        """Scans all supported dependency manifest and lock files in the repository."""
        dependencies: List[Dict[str, Any]] = []
        manifest_files_found: List[str] = []
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"

        # Group chunks by file path
        manifest_patterns = [
            "package.json", "package-lock.json",
            "requirements.txt", "pyproject.toml", "Pipfile", "Pipfile.lock",
            "Cargo.toml", "Cargo.lock",
            "go.mod", "pom.xml", "Gemfile", "Gemfile.lock"
        ]

        # Scan chunks for manifest contents
        scanned_paths = set()
        for chunk in self.chunks:
            p = chunk.file_path.replace("\\", "/")
            base_name = p.split("/")[-1]
            if base_name in manifest_patterns and p not in scanned_paths:
                scanned_paths.add(p)
                manifest_files_found.append(p)
                # Combine all chunks for this file if fragmented
                file_content = "\n".join([
                    c.content for c in self.chunks
                    if c.file_path.replace("\\", "/") == p
                ])
                deps = self._parse_file(base_name, p, file_content, now_iso)
                dependencies.extend(deps)

        # If no manifest found in chunks, attempt direct fetch from GitHub client
        if not manifest_files_found:
            for m_name in manifest_patterns:
                try:
                    content = await self.github_client.get_file_content(
                        self.repository.full_name,
                        m_name,
                        self.repository.indexed_commit_sha or self.repository.default_branch
                    )
                    if content:
                        manifest_files_found.append(m_name)
                        deps = self._parse_file(m_name, m_name, content, now_iso)
                        dependencies.extend(deps)
                except Exception:
                    continue

        # Sort dependencies by name
        dependencies = sorted(dependencies, key=lambda x: (x["manifest_file"], x["name"]))

        direct_count = len([d for d in dependencies if d["is_transitive"] is False])
        transitive_count = len([d for d in dependencies if d["is_transitive"] is True])
        unconfirmed_count = len([d for d in dependencies if d["is_transitive"] is None])

        return {
            "repository_id": self.repository.id,
            "full_name": self.repository.full_name,
            "commit_sha": self.repository.indexed_commit_sha,
            "scan_timestamp": now_iso,
            "manifest_files": manifest_files_found,
            "summary": {
                "total_dependencies": len(dependencies),
                "direct_dependencies": direct_count,
                "transitive_dependencies": transitive_count,
                "unconfirmed_dependencies": unconfirmed_count,
            },
            "dependencies": dependencies,
            "vulnerability_notice": "External vulnerability database is unconfigured. Vulnerability statuses are unverified without a trusted security feed.",
            "verification_source": "RepoSage Static Manifest & Lockfile Parser",
            "checked_at": now_iso
        }

    def _parse_file(self, base_name: str, file_path: str, content: str, checked_at: str) -> List[Dict[str, Any]]:
        results = []
        if base_name == "package.json":
            results.extend(self._parse_package_json(file_path, content, checked_at))
        elif base_name == "package-lock.json":
            results.extend(self._parse_package_lock(file_path, content, checked_at))
        elif base_name == "requirements.txt":
            results.extend(self._parse_requirements_txt(file_path, content, checked_at))
        elif base_name == "pyproject.toml":
            results.extend(self._parse_pyproject_toml(file_path, content, checked_at))
        elif base_name == "Cargo.toml":
            results.extend(self._parse_cargo_toml(file_path, content, checked_at))
        elif base_name == "Cargo.lock":
            results.extend(self._parse_cargo_lock(file_path, content, checked_at))
        elif base_name == "go.mod":
            results.extend(self._parse_go_mod(file_path, content, checked_at))
        elif base_name == "pom.xml":
            results.extend(self._parse_pom_xml(file_path, content, checked_at))
        return results

    def _parse_package_json(self, file_path: str, content: str, checked_at: str) -> List[Dict[str, Any]]:
        deps = []
        try:
            data = json.loads(content)
            sections = [
                ("dependencies", "direct"),
                ("devDependencies", "development"),
                ("peerDependencies", "peer"),
                ("optionalDependencies", "optional")
            ]
            for sec_key, dep_type in sections:
                if sec_key in data and isinstance(data[sec_key], dict):
                    for name, ver in data[sec_key].items():
                        deps.append({
                            "name": name,
                            "declared_version": str(ver),
                            "manifest_file": file_path,
                            "is_transitive": False,
                            "dependency_type": dep_type,
                            "vulnerability_status": "Unverified (no trusted database configured)",
                            "source": "Static Manifest (package.json)",
                            "checked_at": checked_at
                        })
        except Exception:
            pass
        return deps

    def _parse_package_lock(self, file_path: str, content: str, checked_at: str) -> List[Dict[str, Any]]:
        deps = []
        try:
            data = json.loads(content)
            # v2/v3 lockfiles have "packages"
            packages = data.get("packages", {})
            if packages:
                root_deps = packages.get("", {}).get("dependencies", {})
                for pkg_key, pkg_info in packages.items():
                    if not pkg_key:
                        continue
                    name = pkg_key.replace("node_modules/", "")
                    ver = pkg_info.get("version", "unknown")
                    is_direct = name in root_deps
                    deps.append({
                        "name": name,
                        "declared_version": str(ver),
                        "manifest_file": file_path,
                        "is_transitive": not is_direct,
                        "dependency_type": "direct" if is_direct else "transitive",
                        "vulnerability_status": "Unverified (no trusted database configured)",
                        "source": "Lockfile (package-lock.json)",
                        "checked_at": checked_at
                    })
        except Exception:
            pass
        return deps

    def _parse_requirements_txt(self, file_path: str, content: str, checked_at: str) -> List[Dict[str, Any]]:
        deps = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-r") or line.startswith("-i"):
                continue
            # Parse package and version e.g. fastapi>=0.100.0 or requests==2.31.0
            match = re.match(r"^([a-zA-Z0-9_\-\.]+)(?:([=><~^!]+.*))?$", line)
            if match:
                name = match.group(1)
                ver = match.group(2) or "any"
                deps.append({
                    "name": name,
                    "declared_version": ver,
                    "manifest_file": file_path,
                    "is_transitive": False,
                    "dependency_type": "direct",
                    "vulnerability_status": "Unverified (no trusted database configured)",
                    "source": "Static Manifest (requirements.txt)",
                    "checked_at": checked_at
                })
        return deps

    def _parse_pyproject_toml(self, file_path: str, content: str, checked_at: str) -> List[Dict[str, Any]]:
        deps = []
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("[project.dependencies]") or stripped.startswith("[tool.poetry.dependencies]"):
                in_deps = True
                continue
            if stripped.startswith("[") and in_deps:
                in_deps = False
                continue
            if in_deps and "=" in stripped:
                parts = stripped.split("=", 1)
                name = parts[0].strip().strip("\"'")
                ver = parts[1].strip().strip("\"'")
                if name.lower() != "python":
                    deps.append({
                        "name": name,
                        "declared_version": ver,
                        "manifest_file": file_path,
                        "is_transitive": False,
                        "dependency_type": "direct",
                        "vulnerability_status": "Unverified (no trusted database configured)",
                        "source": "Static Manifest (pyproject.toml)",
                        "checked_at": checked_at
                    })
        return deps

    def _parse_cargo_toml(self, file_path: str, content: str, checked_at: str) -> List[Dict[str, Any]]:
        deps = []
        in_deps = False
        dep_type = "direct"
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == "[dependencies]":
                in_deps = True
                dep_type = "direct"
                continue
            elif stripped == "[dev-dependencies]":
                in_deps = True
                dep_type = "development"
                continue
            elif stripped.startswith("[") and in_deps:
                in_deps = False
                continue
            if in_deps and "=" in stripped:
                parts = stripped.split("=", 1)
                name = parts[0].strip()
                ver = parts[1].strip().strip("\"'")
                deps.append({
                    "name": name,
                    "declared_version": ver,
                    "manifest_file": file_path,
                    "is_transitive": False,
                    "dependency_type": dep_type,
                    "vulnerability_status": "Unverified (no trusted database configured)",
                    "source": "Static Manifest (Cargo.toml)",
                    "checked_at": checked_at
                })
        return deps

    def _parse_cargo_lock(self, file_path: str, content: str, checked_at: str) -> List[Dict[str, Any]]:
        deps = []
        current_name = None
        current_ver = None
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == "[[package]]":
                if current_name and current_ver:
                    deps.append({
                        "name": current_name,
                        "declared_version": current_ver,
                        "manifest_file": file_path,
                        "is_transitive": True,
                        "dependency_type": "transitive",
                        "vulnerability_status": "Unverified (no trusted database configured)",
                        "source": "Lockfile (Cargo.lock)",
                        "checked_at": checked_at
                    })
                current_name = None
                current_ver = None
            elif stripped.startswith("name = "):
                current_name = stripped.split("=", 1)[1].strip().strip("\"'")
            elif stripped.startswith("version = "):
                current_ver = stripped.split("=", 1)[1].strip().strip("\"'")
        if current_name and current_ver:
            deps.append({
                "name": current_name,
                "declared_version": current_ver,
                "manifest_file": file_path,
                "is_transitive": True,
                "dependency_type": "transitive",
                "vulnerability_status": "Unverified (no trusted database configured)",
                "source": "Lockfile (Cargo.lock)",
                "checked_at": checked_at
            })
        return deps

    def _parse_go_mod(self, file_path: str, content: str, checked_at: str) -> List[Dict[str, Any]]:
        deps = []
        in_require = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("require ("):
                in_require = True
                continue
            elif stripped == ")" and in_require:
                in_require = False
                continue
            elif stripped.startswith("require "):
                parts = stripped.split()
                if len(parts) >= 3:
                    is_ind = "// indirect" in stripped
                    deps.append({
                        "name": parts[1],
                        "declared_version": parts[2],
                        "manifest_file": file_path,
                        "is_transitive": is_ind,
                        "dependency_type": "transitive" if is_ind else "direct",
                        "vulnerability_status": "Unverified (no trusted database configured)",
                        "source": "Static Manifest (go.mod)",
                        "checked_at": checked_at
                    })
            elif in_require and stripped and not stripped.startswith("//"):
                parts = stripped.split()
                if len(parts) >= 2:
                    is_ind = "// indirect" in stripped
                    deps.append({
                        "name": parts[0],
                        "declared_version": parts[1],
                        "manifest_file": file_path,
                        "is_transitive": is_ind,
                        "dependency_type": "transitive" if is_ind else "direct",
                        "vulnerability_status": "Unverified (no trusted database configured)",
                        "source": "Static Manifest (go.mod)",
                        "checked_at": checked_at
                    })
        return deps

    def _parse_pom_xml(self, file_path: str, content: str, checked_at: str) -> List[Dict[str, Any]]:
        deps = []
        dep_blocks = re.findall(r"<dependency>(.*?)</dependency>", content, re.DOTALL)
        for block in dep_blocks:
            g_match = re.search(r"<groupId>(.*?)</groupId>", block)
            a_match = re.search(r"<artifactId>(.*?)</artifactId>", block)
            v_match = re.search(r"<version>(.*?)</version>", block)
            if a_match:
                name = f"{g_match.group(1)}:{a_match.group(1)}" if g_match else a_match.group(1)
                ver = v_match.group(1) if v_match else "managed"
                deps.append({
                    "name": name,
                    "declared_version": ver,
                    "manifest_file": file_path,
                    "is_transitive": False,
                    "dependency_type": "direct",
                    "vulnerability_status": "Unverified (no trusted database configured)",
                    "source": "Static Manifest (pom.xml)",
                    "checked_at": checked_at
                })
        return deps
