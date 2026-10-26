"""Read the numeric parameter block of cad/darkroom.scad without running OpenSCAD.

Only top-level `name = expression;` assignments are evaluated, in file order, with a
tiny arithmetic subset (numbers, vectors, indexing, + - * /, parentheses, names that
were already assigned). Anything else (colours with ternaries, strings, module bodies)
is skipped. Feature anchors and split planes are computed from these values, so the
drawing follows the CAD instead of a copied table of numbers.
"""
from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

ASSIGN = re.compile(r"^([A-Za-z_]\w*)\s*=\s*([^;]+);")


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _top_level(text: str) -> str:
    """Drop everything inside { } so module-local assignments are not read as parameters."""
    out, depth = [], 0
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0 or ch == "\n":
            out.append(ch)
    return "".join(out)


class _Eval(ast.NodeVisitor):
    def __init__(self, env):
        self.env = env

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return float(node.value)
        raise ValueError("non-numeric constant")

    def visit_Name(self, node):
        if node.id not in self.env:
            raise ValueError(f"unknown name {node.id}")
        return self.env[node.id]

    def visit_List(self, node):
        return [self.visit(e) for e in node.elts]

    def visit_Subscript(self, node):
        seq = self.visit(node.value)
        idx = int(self.visit(node.slice))
        return seq[idx]

    def visit_UnaryOp(self, node):
        v = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.UAdd):
            return v
        raise ValueError("unsupported unary op")

    def visit_BinOp(self, node):
        a, b = self.visit(node.left), self.visit(node.right)
        if isinstance(a, list) or isinstance(b, list):
            raise ValueError("vector arithmetic not needed")
        ops = {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b, ast.Div: lambda: a / b}
        for op, fn in ops.items():
            if isinstance(node.op, op):
                return fn()
        raise ValueError("unsupported operator")

    def generic_visit(self, node):
        raise ValueError(f"unsupported syntax {type(node).__name__}")


def read_params(scad_path: Path) -> dict:
    env: dict = {}
    for line in _top_level(_strip_comments(scad_path.read_text())).splitlines():
        # several assignments may share a line: `W = 80;  D = 84;  H = 80;`
        for stmt in line.split(";"):
            m = ASSIGN.match(stmt.strip() + ";")
            if not m:
                continue
            name, expr = m.group(1), m.group(2).strip()
            if '"' in expr or "?" in expr:
                continue
            try:
                env[name] = _Eval(env).visit(ast.parse(expr, mode="eval"))
            except (ValueError, SyntaxError, IndexError, TypeError):
                continue
    return env


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
