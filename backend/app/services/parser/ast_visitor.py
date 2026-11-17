import ast
import re
from typing import List, Dict, Any, Optional


class ParsedSymbol:
    def __init__(
        self,
        name: str,
        symbol_type: str,
        start_line: int,
        end_line: int,
        content: str,
        docstring: Optional[str] = None
    ):
        self.name = name
        self.symbol_type = symbol_type
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.docstring = docstring


class ParsedRelationship:
    def __init__(
        self,
        relationship_type: str,  # imports, calls, defines
        source_symbol: str,
        target_symbol: str,
        target_file: Optional[str],
        line_number: int,
        evidence_snippet: str
    ):
        self.relationship_type = relationship_type
        self.source_symbol = source_symbol
        self.target_symbol = target_symbol
        self.target_file = target_file
        self.line_number = line_number
        self.evidence_snippet = evidence_snippet


def parse_python_ast(code: str, file_path: str) -> Dict[str, Any]:
    """
    Parses Python source code using standard library `ast`.
    Extracts top-level and class-level symbols (functions, classes, methods),
    import statements, and function calls.
    """
    lines = code.splitlines(keepends=True)
    symbols: List[ParsedSymbol] = []
    relationships: List[ParsedRelationship] = []

    try:
        tree = ast.parse(code, filename=file_path)
    except SyntaxError:
        # Fallback to empty if syntax error in code
        return {"symbols": [], "relationships": []}

    class CodeVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_class: Optional[str] = None

        def visit_Import(self, node: ast.Import):
            line_no = node.lineno
            evidence = lines[line_no - 1].strip() if 0 <= line_no - 1 < len(lines) else ""
            for alias in node.names:
                relationships.append(
                    ParsedRelationship(
                        relationship_type="imports",
                        source_symbol=file_path,
                        target_symbol=alias.name,
                        target_file=alias.name.replace(".", "/") + ".py",
                        line_number=line_no,
                        evidence_snippet=evidence
                    )
                )
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom):
            line_no = node.lineno
            evidence = lines[line_no - 1].strip() if 0 <= line_no - 1 < len(lines) else ""
            module = node.module or ""
            for alias in node.names:
                target_sym = f"{module}.{alias.name}" if module else alias.name
                target_file = module.replace(".", "/") + ".py" if module else None
                relationships.append(
                    ParsedRelationship(
                        relationship_type="imports",
                        source_symbol=file_path,
                        target_symbol=target_sym,
                        target_file=target_file,
                        line_number=line_no,
                        evidence_snippet=evidence
                    )
                )
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef):
            start = node.lineno
            end = getattr(node, "end_lineno", start + len(node.body))
            content = "".join(lines[start - 1:end])
            docstring = ast.get_docstring(node)
            symbols.append(
                ParsedSymbol(
                    name=node.name,
                    symbol_type="class",
                    start_line=start,
                    end_line=end,
                    content=content,
                    docstring=docstring
                )
            )

            # Check inheritance
            for base in node.bases:
                base_name = getattr(base, "id", None) or getattr(base, "attr", str(base))
                evidence = lines[start - 1].strip() if 0 <= start - 1 < len(lines) else ""
                relationships.append(
                    ParsedRelationship(
                        relationship_type="inherits",
                        source_symbol=node.name,
                        target_symbol=str(base_name),
                        target_file=None,
                        line_number=start,
                        evidence_snippet=evidence
                    )
                )

            old_class = self.current_class
            self.current_class = node.name
            self.generic_visit(node)
            self.current_class = old_class

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self._handle_func(node, is_async=False)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self._handle_func(node, is_async=True)

        def _handle_func(self, node: Any, is_async: bool):
            start = node.lineno
            end = getattr(node, "end_lineno", start + len(node.body))
            content = "".join(lines[start - 1:end])
            docstring = ast.get_docstring(node)
            sym_name = f"{self.current_class}.{node.name}" if self.current_class else node.name
            sym_type = "method" if self.current_class else "function"

            symbols.append(
                ParsedSymbol(
                    name=sym_name,
                    symbol_type=sym_type,
                    start_line=start,
                    end_line=end,
                    content=content,
                    docstring=docstring
                )
            )
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name and func_name not in {"print", "len", "range", "str", "int", "dict", "list", "set"}:
                line_no = node.lineno
                evidence = lines[line_no - 1].strip() if 0 <= line_no - 1 < len(lines) else ""
                source_sym = self.current_class or file_path
                relationships.append(
                    ParsedRelationship(
                        relationship_type="calls",
                        source_symbol=source_sym,
                        target_symbol=func_name,
                        target_file=None,
                        line_number=line_no,
                        evidence_snippet=evidence
                    )
                )
            self.generic_visit(node)

    visitor = CodeVisitor()
    visitor.visit(tree)
    return {"symbols": symbols, "relationships": relationships}


def parse_js_ts_symbols(code: str, file_path: str) -> Dict[str, Any]:
    """
    Extracts functions, classes, and imports from JavaScript/TypeScript files.
    """
    lines = code.splitlines(keepends=True)
    symbols: List[ParsedSymbol] = []
    relationships: List[ParsedRelationship] = []

    # Import regex: import ... from '...'; or require('...')
    import_regex = re.compile(r"""(?:import\s+(?:[\w*\s{},]+)\s+from\s+['"]([^'"]+)['"]|import\s+['"]([^'"]+)['"]|const\s+\w+\s*=\s*require\(['"]([^'"]+)['"]\))""")
    
    # Class regex: class ClassName
    class_regex = re.compile(r"class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([A-Za-z0-9_$]+))?")

    # Function regex: function name(...) or const/let name = (...) =>
    func_regex = re.compile(r"(?:(?:async\s+)?function\s+([A-Za-z0-9_$]+)|(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)")

    for i, line in enumerate(lines):
        line_no = i + 1
        stripped = line.strip()

        # Check imports
        imp_match = import_regex.search(stripped)
        if imp_match:
            target_module = imp_match.group(1) or imp_match.group(2) or imp_match.group(3)
            if target_module:
                relationships.append(
                    ParsedRelationship(
                        relationship_type="imports",
                        source_symbol=file_path,
                        target_symbol=target_module,
                        target_file=target_module + (".ts" if not target_module.endswith((".ts", ".js")) else ""),
                        line_number=line_no,
                        evidence_snippet=stripped
                    )
                )

        # Check classes
        cls_match = class_regex.search(stripped)
        if cls_match:
            cls_name = cls_match.group(1)
            # Find approximate end of class (at least 20 lines or end of file)
            end_line = min(len(lines), line_no + 30)
            symbols.append(
                ParsedSymbol(
                    name=cls_name,
                    symbol_type="class",
                    start_line=line_no,
                    end_line=end_line,
                    content="".join(lines[line_no - 1:end_line])
                )
            )

        # Check functions
        fn_match = func_regex.search(stripped)
        if fn_match:
            fn_name = fn_match.group(1) or fn_match.group(2)
            if fn_name:
                end_line = min(len(lines), line_no + 25)
                symbols.append(
                    ParsedSymbol(
                        name=fn_name,
                        symbol_type="function",
                        start_line=line_no,
                        end_line=end_line,
                        content="".join(lines[line_no - 1:end_line])
                    )
                )

    return {"symbols": symbols, "relationships": relationships}
