import os
from typing import Dict, List, Optional
from app.services.languages.models import LanguageAdapter, LanguageCategory


class LanguageRegistry:
    """
    Extensible Language Adapter Registry.
    Defines language aliases, supported extensions, recognized filenames,
    parser availability, and chunking behavior.
    """

    def __init__(self):
        self._adapters_by_name: Dict[str, LanguageAdapter] = {}
        self._extension_map: Dict[str, LanguageAdapter] = {}
        self._filename_map: Dict[str, LanguageAdapter] = {}
        self._alias_map: Dict[str, LanguageAdapter] = {}
        self._initialize_builtins()

    def register(self, adapter: LanguageAdapter) -> None:
        """Registers a new or custom language adapter."""
        canonical = adapter.name.lower()
        self._adapters_by_name[canonical] = adapter

        for ext in adapter.extensions:
            self._extension_map[ext.lower()] = adapter

        for fname in adapter.filenames:
            self._filename_map[fname.lower()] = adapter

        for alias in adapter.aliases:
            self._alias_map[alias.lower()] = adapter

    def get_by_name(self, name: str) -> Optional[LanguageAdapter]:
        if not name:
            return None
        clean = name.lower().strip()
        return self._adapters_by_name.get(clean) or self._alias_map.get(clean)

    def get_by_extension(self, extension: str) -> Optional[LanguageAdapter]:
        if not extension:
            return None
        ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        return self._extension_map.get(ext)

    def get_by_filename(self, filename: str) -> Optional[LanguageAdapter]:
        if not filename:
            return None
        base = os.path.basename(filename).lower()
        return self._filename_map.get(base)

    def list_all(self) -> List[LanguageAdapter]:
        return list(self._adapters_by_name.values())

    def _initialize_builtins(self) -> None:
        adapters = [
            # 1. Python
            LanguageAdapter(
                name="python",
                display_name="Python",
                extensions=[".py", ".pyi", ".pyw"],
                aliases=["py", "python3"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="ast"
            ),
            # 2. JavaScript
            LanguageAdapter(
                name="javascript",
                display_name="JavaScript",
                extensions=[".js", ".jsx", ".mjs", ".cjs"],
                aliases=["js", "jsx", "node"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 3. TypeScript
            LanguageAdapter(
                name="typescript",
                display_name="TypeScript",
                extensions=[".ts", ".tsx", ".mts", ".cts"],
                aliases=["ts", "tsx"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 4. Java
            LanguageAdapter(
                name="java",
                display_name="Java",
                extensions=[".java"],
                aliases=["jvm"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 5. C
            LanguageAdapter(
                name="c",
                display_name="C",
                extensions=[".c", ".h"],
                aliases=["c-lang"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 6. C++
            LanguageAdapter(
                name="cpp",
                display_name="C++",
                extensions=[".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".c++", ".h++"],
                aliases=["cplusplus", "c++"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 7. C#
            LanguageAdapter(
                name="csharp",
                display_name="C#",
                extensions=[".cs"],
                aliases=["c#", "dotnet"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 8. Go
            LanguageAdapter(
                name="go",
                display_name="Go",
                extensions=[".go"],
                aliases=["golang"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 9. Rust
            LanguageAdapter(
                name="rust",
                display_name="Rust",
                extensions=[".rs"],
                aliases=["rs"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 10. PHP
            LanguageAdapter(
                name="php",
                display_name="PHP",
                extensions=[".php", ".phtml", ".php5", ".php7", ".php8"],
                aliases=["php3", "php4"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 11. Ruby
            LanguageAdapter(
                name="ruby",
                display_name="Ruby",
                extensions=[".rb", ".rake", ".gemspec"],
                filenames=["gemfile", "rakefile"],
                aliases=["rb", "rails"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 12. Kotlin
            LanguageAdapter(
                name="kotlin",
                display_name="Kotlin",
                extensions=[".kt", ".kts"],
                aliases=["kt"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 13. Swift
            LanguageAdapter(
                name="swift",
                display_name="Swift",
                extensions=[".swift"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 14. Scala
            LanguageAdapter(
                name="scala",
                display_name="Scala",
                extensions=[".scala", ".sc"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 15. Dart
            LanguageAdapter(
                name="dart",
                display_name="Dart",
                extensions=[".dart"],
                aliases=["flutter"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=True,
                chunking_strategy="symbol_regex"
            ),
            # 16. Elixir
            LanguageAdapter(
                name="elixir",
                display_name="Elixir",
                extensions=[".ex", ".exs"],
                aliases=["ex"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 17. Erlang
            LanguageAdapter(
                name="erlang",
                display_name="Erlang",
                extensions=[".erl", ".hrl"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 18. Haskell
            LanguageAdapter(
                name="haskell",
                display_name="Haskell",
                extensions=[".hs", ".lhs"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 19. Lua
            LanguageAdapter(
                name="lua",
                display_name="Lua",
                extensions=[".lua"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 20. R
            LanguageAdapter(
                name="r",
                display_name="R",
                extensions=[".r", ".R"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 21. Julia
            LanguageAdapter(
                name="julia",
                display_name="Julia",
                extensions=[".jl"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 22. Perl
            LanguageAdapter(
                name="perl",
                display_name="Perl",
                extensions=[".pl", ".pm", ".t"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 23. Bash / Shell
            LanguageAdapter(
                name="bash",
                display_name="Bash / Shell",
                extensions=[".sh", ".bash", ".zsh", ".ksh"],
                aliases=["shell", "sh", "zsh"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 24. PowerShell
            LanguageAdapter(
                name="powershell",
                display_name="PowerShell",
                extensions=[".ps1", ".psm1", ".psd1"],
                aliases=["ps1", "pwsh"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 25. SQL
            LanguageAdapter(
                name="sql",
                display_name="SQL",
                extensions=[".sql", ".pgsql", ".mysql"],
                category=LanguageCategory.DATA,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 26. HTML
            LanguageAdapter(
                name="html",
                display_name="HTML",
                extensions=[".html", ".htm"],
                category=LanguageCategory.MARKUP,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 27. CSS
            LanguageAdapter(
                name="css",
                display_name="CSS / SCSS",
                extensions=[".css", ".scss", ".sass", ".less"],
                aliases=["scss", "sass", "less"],
                category=LanguageCategory.MARKUP,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 28. Vue
            LanguageAdapter(
                name="vue",
                display_name="Vue",
                extensions=[".vue"],
                category=LanguageCategory.MARKUP,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 29. Svelte
            LanguageAdapter(
                name="svelte",
                display_name="Svelte",
                extensions=[".svelte"],
                category=LanguageCategory.MARKUP,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 30. Solidity
            LanguageAdapter(
                name="solidity",
                display_name="Solidity",
                extensions=[".sol"],
                category=LanguageCategory.PROGRAMMING,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 31. YAML
            LanguageAdapter(
                name="yaml",
                display_name="YAML",
                extensions=[".yaml", ".yml"],
                category=LanguageCategory.CONFIG,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 32. TOML
            LanguageAdapter(
                name="toml",
                display_name="TOML",
                extensions=[".toml"],
                filenames=["cargo.toml", "pyproject.toml"],
                category=LanguageCategory.CONFIG,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 33. JSON
            LanguageAdapter(
                name="json",
                display_name="JSON",
                extensions=[".json", ".json5"],
                category=LanguageCategory.DATA,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 34. Markdown
            LanguageAdapter(
                name="markdown",
                display_name="Markdown",
                extensions=[".md", ".markdown", ".mdown"],
                aliases=["md"],
                category=LanguageCategory.PROSE,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 35. Recognized Build & Docker Configurations
            LanguageAdapter(
                name="dockerfile",
                display_name="Dockerfile",
                filenames=["dockerfile", "containerfile"],
                extensions=[".dockerfile"],
                category=LanguageCategory.CONFIG,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            LanguageAdapter(
                name="makefile",
                display_name="Makefile",
                filenames=["makefile", "gnumakefile"],
                extensions=[".mk"],
                category=LanguageCategory.CONFIG,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            LanguageAdapter(
                name="config",
                display_name="Configuration",
                filenames=[
                    ".editorconfig", ".gitattributes", ".dockerignore",
                    ".npmrc", ".yarnrc", ".browserslistrc", ".env.example"
                ],
                extensions=[".conf", ".ini", ".cfg", ".properties"],
                category=LanguageCategory.CONFIG,
                parser_available=False,
                chunking_strategy="line_window"
            ),
            # 36. Generic Text / Code Fallback (for any readable code/text not explicitly listed)
            LanguageAdapter(
                name="generic_code",
                display_name="Generic Code/Text",
                extensions=[],
                category=LanguageCategory.UNKNOWN,
                parser_available=False,
                chunking_strategy="line_window"
            ),
        ]

        for adapter in adapters:
            self.register(adapter)


# Global singleton instance
language_registry = LanguageRegistry()
