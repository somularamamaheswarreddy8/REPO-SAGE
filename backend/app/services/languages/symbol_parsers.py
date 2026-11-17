import re
from typing import List, Dict, Any, Optional
from app.services.parser.ast_visitor import ParsedSymbol, ParsedRelationship


def extract_regex_symbols(code: str, file_path: str, language: str) -> List[ParsedSymbol]:
    """
    Extracts structural symbols (classes, functions, interfaces, structs)
    for compiled and high-level languages without requiring native compilers.
    Preserves exact 1-indexed start_line and end_line.
    """
    symbols: List[ParsedSymbol] = []
    lines = code.splitlines(keepends=True)
    if not lines:
        return symbols

    # Language-specific symbol declaration patterns
    patterns: Dict[str, List[Dict[str, Any]]] = {
        "go": [
            {"type": "function", "regex": re.compile(r"^func\s+(?:\(.*?\)\s+)?([A-Za-z0-9_]+)\s*\(")},
            {"type": "struct", "regex": re.compile(r"^type\s+([A-Za-z0-9_]+)\s+struct\b")},
            {"type": "interface", "regex": re.compile(r"^type\s+([A-Za-z0-9_]+)\s+interface\b")}
        ],
        "rust": [
            {"type": "function", "regex": re.compile(r"^(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z0-9_]+)\s*")},
            {"type": "struct", "regex": re.compile(r"^(?:pub\s+)?struct\s+([A-Za-z0-9_]+)\b")},
            {"type": "enum", "regex": re.compile(r"^(?:pub\s+)?enum\s+([A-Za-z0-9_]+)\b")},
            {"type": "trait", "regex": re.compile(r"^(?:pub\s+)?trait\s+([A-Za-z0-9_]+)\b")},
            {"type": "impl", "regex": re.compile(r"^impl(?:\s+<.*?>)?\s+([A-Za-z0-9_]+)")}
        ],
        "java": [
            {"type": "class", "regex": re.compile(r"^(?:public|private|protected|abstract|final|\s)*class\s+([A-Za-z0-9_]+)")},
            {"type": "interface", "regex": re.compile(r"^(?:public|private|protected|\s)*interface\s+([A-Za-z0-9_]+)")},
            {"type": "method", "regex": re.compile(r"^(?:public|private|protected|static|final|\s)+[\w<>\[\]]+\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{?")}
        ],
        "csharp": [
            {"type": "class", "regex": re.compile(r"^(?:public|private|protected|internal|abstract|sealed|\s)*class\s+([A-Za-z0-9_]+)")},
            {"type": "interface", "regex": re.compile(r"^(?:public|private|protected|internal|\s)*interface\s+([A-Za-z0-9_]+)")},
            {"type": "method", "regex": re.compile(r"^(?:public|private|protected|internal|static|async|\s)+[\w<>\[\]]+\s+([A-Za-z0-9_]+)\s*\(")}
        ],
        "cpp": [
            {"type": "class", "regex": re.compile(r"^(?:class|struct)\s+([A-Za-z0-9_]+)(?:\s*:\s*[^{]+)?\s*\{?")},
            {"type": "function", "regex": re.compile(r"^(?:[\w:*&<>]+\s+)+([A-Za-z0-9_]+)\s*\([^;]*\)\s*(?:const)?\s*\{?")}
        ],
        "c": [
            {"type": "struct", "regex": re.compile(r"^(?:typedef\s+)?struct\s+([A-Za-z0-9_]+)")},
            {"type": "function", "regex": re.compile(r"^(?:[\w*]+\s+)+([A-Za-z0-9_]+)\s*\([^;]*\)\s*\{?")}
        ],
        "ruby": [
            {"type": "class", "regex": re.compile(r"^\s*class\s+([A-Za-z0-9_:]+)")},
            {"type": "module", "regex": re.compile(r"^\s*module\s+([A-Za-z0-9_:]+)")},
            {"type": "function", "regex": re.compile(r"^\s*def\s+([A-Za-z0-9_!?=]+)")}
        ],
        "php": [
            {"type": "class", "regex": re.compile(r"^(?:abstract|final|\s)*class\s+([A-Za-z0-9_]+)")},
            {"type": "function", "regex": re.compile(r"^(?:public|private|protected|static|\s)*function\s+([A-Za-z0-9_]+)\s*\(")}
        ],
        "kotlin": [
            {"type": "class", "regex": re.compile(r"^(?:data|enum|sealed|abstract|\s)*class\s+([A-Za-z0-9_]+)")},
            {"type": "function", "regex": re.compile(r"^(?:override|suspend|private|public|\s)*fun\s+([A-Za-z0-9_]+)\s*\(")}
        ],
        "swift": [
            {"type": "class", "regex": re.compile(r"^(?:public|private|open|final|\s)*(?:class|struct|protocol)\s+([A-Za-z0-9_]+)")},
            {"type": "function", "regex": re.compile(r"^(?:public|private|open|\s)*func\s+([A-Za-z0-9_]+)\s*\(")}
        ],
        "scala": [
            {"type": "class", "regex": re.compile(r"^(?:case|abstract|\s)*(?:class|object|trait)\s+([A-Za-z0-9_]+)")},
            {"type": "function", "regex": re.compile(r"^\s*def\s+([A-Za-z0-9_]+)\s*(?:\[.*?\])?\s*\(")}
        ],
        "dart": [
            {"type": "class", "regex": re.compile(r"^(?:abstract|\s)*class\s+([A-Za-z0-9_]+)")},
            {"type": "function", "regex": re.compile(r"^[\w<>\[\]?]+\s+([A-Za-z0-9_]+)\s*\(")}
        ]
    }

    lang_patterns = patterns.get(language, [])
    if not lang_patterns:
        return symbols

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "/*", "*", "#")):
            continue

        for p in lang_patterns:
            match = p["regex"].search(stripped)
            if match:
                name = match.group(1)
                start_line = i + 1
                
                # Estimate block end using indentation or brace counting
                end_line = min(len(lines), start_line + 40)
                
                # If brace-based language, try simple brace balancing
                if "{" in line or (i + 1 < len(lines) and "{" in lines[i + 1]):
                    depth = 0
                    found_open = False
                    for j in range(i, len(lines)):
                        cur = lines[j]
                        depth += cur.count("{") - cur.count("}")
                        if "{" in cur:
                            found_open = True
                        if found_open and depth <= 0:
                            end_line = j + 1
                            break

                symbol_content = "".join(lines[start_line - 1:end_line])
                symbols.append(
                    ParsedSymbol(
                        name=name,
                        symbol_type=p["type"],
                        start_line=start_line,
                        end_line=end_line,
                        content=symbol_content
                    )
                )
                break

    return symbols
