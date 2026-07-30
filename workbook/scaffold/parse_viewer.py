#!/usr/bin/env python3
"""
Parser output viewer for the teaching scaffold.

By default, this script prints the AST as an S-expression. It uses the same
lexer/parser modules as student programs, so the output shows exactly what the
provided parser returns.
"""

import argparse
import json
import re
import sys
from dataclasses import fields
from typing import Any, List

from ast_def import *
from lexer import TK_EOF, TK_PUNCT, preprocess, tokenize
from parser import parse


class Sym(str):
    """S-expression symbol. Plain str values are rendered as quoted strings."""


BINARY_NAMES = {
    ND_ADD: "add",
    ND_SUB: "sub",
    ND_MUL: "mul",
    ND_DIV: "div",
    ND_MOD: "mod",
    ND_EQ: "eq",
    ND_NE: "ne",
    ND_LT: "lt",
    ND_LE: "le",
    ND_AND: "and",
    ND_OR: "or",
}

UNARY_NAMES = {
    ND_NEG: "neg",
    ND_NOT: "not",
    ND_ADDR: "addr",
    ND_DEREF: "deref",
    ND_PREINC: "preinc",
    ND_PREDEC: "predec",
}


def sym(value: str) -> Sym:
    return Sym(value)


def quote_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def format_type(ty_str: str) -> Any:
    """Convert the scaffold's simple ty_str into a structured S-expression."""
    ty = ty_str.strip()
    if not ty:
        return [sym("type"), ""]

    ptr_count = 0
    while ty.endswith("*"):
        ptr_count += 1
        ty = ty[:-1].strip()

    if ty in ("int", "char", "void"):
        expr: Any = sym(ty)
    elif ty == "struct":
        expr = [sym("struct")]
    elif ty.startswith("struct "):
        tag = ty[len("struct ") :].strip()
        expr = [sym("struct"), tag] if tag else [sym("struct")]
    else:
        expr = [sym("type"), ty]

    for _ in range(ptr_count):
        expr = [sym("ptr"), expr]
    return expr


def line_attr(node: Node, show_line: bool) -> List[Any]:
    return [sym(":line"), node.line] if show_line and node.line else []


def type_attr(node: Node) -> List[Any]:
    return [sym(":type"), format_type(node.ty_str)] if node.ty_str else []


def param_to_sexp(node: Node, show_line: bool) -> Any:
    head: List[Any] = [sym("param")]
    if node.name:
        head.append(node.name)
    head.extend(type_attr(node))
    head.extend(line_attr(node, show_line))
    return head


def node_to_sexp(node: Node, show_line: bool = False) -> Any:
    kind = node.kind

    if kind == ND_NUM:
        return [sym("num"), node.val, *line_attr(node, show_line)]
    if kind == ND_STR:
        return [sym("str"), node.sval, *line_attr(node, show_line)]
    if kind == ND_VAR:
        return [sym("var"), node.name, *line_attr(node, show_line)]
    if kind == ND_CALL:
        return [
            sym("call"),
            node.name,
            *line_attr(node, show_line),
            [sym("args"), *[node_to_sexp(arg, show_line) for arg in node.args]],
        ]
    if kind == ND_ASSIGN:
        return [
            sym("assign"),
            *line_attr(node, show_line),
            node_to_sexp(node.lhs, show_line),
            node_to_sexp(node.rhs, show_line),
        ]
    if kind in BINARY_NAMES:
        return [
            sym(BINARY_NAMES[kind]),
            *line_attr(node, show_line),
            node_to_sexp(node.lhs, show_line),
            node_to_sexp(node.rhs, show_line),
        ]
    if kind in UNARY_NAMES:
        return [
            sym(UNARY_NAMES[kind]),
            *line_attr(node, show_line),
            node_to_sexp(node.operand, show_line),
        ]
    if kind == ND_INDEX:
        return [
            sym("index"),
            *line_attr(node, show_line),
            node_to_sexp(node.lhs, show_line),
            node_to_sexp(node.rhs, show_line),
        ]
    if kind == ND_MEMBER:
        op = "->" if node.is_arrow else "."
        return [
            sym("member"),
            op,
            node.name,
            *line_attr(node, show_line),
            node_to_sexp(node.operand, show_line),
        ]
    if kind == ND_COND:
        return [
            sym("ternary"),
            *line_attr(node, show_line),
            node_to_sexp(node.cond, show_line),
            node_to_sexp(node.then, show_line),
            node_to_sexp(node.else_, show_line),
        ]
    if kind == ND_SIZEOF_TYPE:
        return [sym("sizeof-type"), format_type(node.ty_str), *line_attr(node, show_line)]
    if kind == ND_BLOCK:
        return [
            sym("block"),
            *line_attr(node, show_line),
            *[node_to_sexp(stmt, show_line) for stmt in node.stmts],
        ]
    if kind == ND_EXPRSTMT:
        items: List[Any] = [sym("exprstmt"), *line_attr(node, show_line)]
        if node.operand is not None:
            items.append(node_to_sexp(node.operand, show_line))
        return items
    if kind == ND_RETURN:
        items = [sym("return"), *line_attr(node, show_line)]
        if node.operand is not None:
            items.append(node_to_sexp(node.operand, show_line))
        return items
    if kind == ND_BREAK:
        return [sym("break"), *line_attr(node, show_line)]
    if kind == ND_CONTINUE:
        return [sym("continue"), *line_attr(node, show_line)]
    if kind == ND_IF:
        items = [
            sym("if"),
            *line_attr(node, show_line),
            [sym("cond"), node_to_sexp(node.cond, show_line)],
            [sym("then"), node_to_sexp(node.then, show_line)],
        ]
        if node.else_ is not None:
            items.append([sym("else"), node_to_sexp(node.else_, show_line)])
        return items
    if kind == ND_WHILE:
        return [
            sym("while"),
            *line_attr(node, show_line),
            [sym("cond"), node_to_sexp(node.cond, show_line)],
            [sym("body"), node_to_sexp(node.body, show_line)],
        ]
    if kind == ND_FOR:
        return [
            sym("for"),
            *line_attr(node, show_line),
            [sym("init"), node_to_sexp(node.init, show_line) if node.init else sym("none")],
            [sym("cond"), node_to_sexp(node.cond, show_line) if node.cond else sym("none")],
            [sym("step"), node_to_sexp(node.step, show_line) if node.step else sym("none")],
            [sym("body"), node_to_sexp(node.body, show_line)],
        ]
    if kind == ND_DECL:
        return [sym("decl"), node.name, *type_attr(node), *line_attr(node, show_line)]
    if kind == ND_FUNCDEF:
        return [
            sym("funcdef"),
            node.name,
            *type_attr(node),
            *line_attr(node, show_line),
            [sym("params"), *[param_to_sexp(param, show_line) for param in node.params]],
            node_to_sexp(node.body, show_line),
        ]
    if kind == ND_FUNCPROTO:
        return [
            sym("funcproto"),
            node.name,
            *type_attr(node),
            *line_attr(node, show_line),
            [sym("params"), *[param_to_sexp(param, show_line) for param in node.params]],
        ]

    return [sym("unknown"), kind, *line_attr(node, show_line)]


def program_to_sexp(program: List[Node], show_line: bool = False) -> Any:
    return [sym("program"), *[node_to_sexp(node, show_line) for node in program]]


def is_flat(expr: Any) -> bool:
    return not isinstance(expr, list) or all(not isinstance(item, list) for item in expr)


def render_atom(value: Any) -> str:
    if isinstance(value, Sym):
        return str(value)
    if isinstance(value, str):
        return quote_string(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "none"
    return str(value)


def render_sexp(expr: Any, indent: int = 0) -> str:
    if not isinstance(expr, list):
        return render_atom(expr)
    if not expr:
        return "()"
    if is_flat(expr):
        return "(" + " ".join(render_atom(item) for item in expr) + ")"

    prefix: List[Any] = []
    rest_start = 0
    for i, item in enumerate(expr):
        if isinstance(item, list) and not is_flat(item):
            rest_start = i
            break
        prefix.append(item)
    else:
        return "(" + " ".join(render_sexp(item) for item in expr) + ")"

    pad = " " * indent
    child_pad = " " * (indent + 2)
    first = pad + "(" + " ".join(render_sexp(item) for item in prefix)
    lines = [first]
    for item in expr[rest_start:]:
        lines.append(child_pad + render_sexp(item, indent + 2).lstrip())
    lines[-1] += ")"
    return "\n".join(lines)


def dot_quote(value: str) -> str:
    """Escape a string for use as a DOT quoted attribute value."""
    return json.dumps(str(value), ensure_ascii=False)


def node_to_dot_label(node: Node, show_line: bool = False) -> str:
    """Build a DOT node label string from an AST node."""
    parts = [node.kind]
    if node.name:
        parts.append(quote_string(node.name))
    if node.kind == ND_NUM:
        parts.append(str(node.val))
    if node.kind == ND_STR:
        parts.append(quote_string(node.sval))
    if node.kind == ND_MEMBER:
        parts.append("->" if node.is_arrow else ".")
    if node.ty_str:
        parts.append(":type " + render_sexp(format_type(node.ty_str)))
    if show_line and node.line:
        parts.append(f"line {node.line}")
    return "\n".join(parts)


def render_dot(program: List[Node], show_line: bool = False) -> str:
    """Render an AST program as a Graphviz DOT digraph string."""
    counter = [1]

    def fresh_id() -> int:
        c = counter[0]
        counter[0] += 1
        return c

    lines: List[str] = []
    def emit(s: str) -> None:
        lines.append(s)

    emit("digraph AST {")
    emit('  graph [rankdir=TB];')
    emit('  node [shape=box, fontname="monospace"];')
    emit('  edge [fontname="monospace"];')
    emit("")

    root_id = fresh_id()
    emit(f'  n{root_id} [label={dot_quote("Program")}];')

    def walk_node(parent_id: int, edge_label: str, node: Node, child_index: int = -1) -> None:
        if node is None:
            return
        nid = fresh_id()
        label = dot_quote(node_to_dot_label(node, show_line))
        emit(f'  n{nid} [label={label}];')
        suffix = f"[{child_index}]" if child_index >= 0 else ""
        elabel = dot_quote(edge_label + suffix)
        emit(f'  n{parent_id} -> n{nid} [label={elabel}];')

        for fname, fval in [
            ("lhs", node.lhs),
            ("rhs", node.rhs),
            ("cond", node.cond),
            ("then", node.then),
            ("else", node.else_),
            ("init", node.init),
            ("step", node.step),
            ("body", node.body),
            ("operand", node.operand),
        ]:
            if fval is not None:
                walk_node(nid, fname, fval)

        for fname, child_list in [
            ("stmts", node.stmts),
            ("args", node.args),
            ("params", node.params),
        ]:
            for i, child in enumerate(child_list):
                walk_node(nid, fname, child, i)

    for i, node in enumerate(program):
        walk_node(root_id, "top", node, i)

    emit("")
    emit("}")
    return "\n".join(lines)


def node_to_dict(node: Node, show_line: bool = True) -> dict:
    result = {"kind": node.kind}
    for field in fields(Node):
        name = field.name
        value = getattr(node, name)
        if name == "kind":
            continue
        if value is None or value == [] or value == "":
            continue
        if name == "val" and node.kind != ND_NUM:
            continue
        if name == "line" and (not show_line or value == 0):
            continue
        if name == "is_arrow" and node.kind != ND_MEMBER:
            continue
        if isinstance(value, bool) and value is False and name != "is_arrow":
            continue
        if name == "ty_str":
            result["ty_str"] = value
            result["type_sexp"] = render_sexp(format_type(value))
            continue
        if isinstance(value, Node):
            result[name] = node_to_dict(value, show_line)
        elif isinstance(value, list):
            result[name] = [node_to_dict(item, show_line) if isinstance(item, Node) else item for item in value]
        else:
            result[name] = value
    return result


def render_tree_node(node: Node, indent: int = 0, show_line: bool = False) -> List[str]:
    label = node.kind
    details = []
    if node.name:
        details.append(quote_string(node.name))
    if node.ty_str:
        details.append(":type " + render_sexp(format_type(node.ty_str)))
    if node.kind == ND_NUM:
        details.append(str(node.val))
    if node.kind == ND_STR:
        details.append(quote_string(node.sval))
    if show_line and node.line:
        details.append(f":line {node.line}")
    line = " " * indent + label + ((" " + " ".join(details)) if details else "")
    lines = [line]
    for child in (node.lhs, node.rhs, node.cond, node.then, node.else_, node.init, node.step, node.body, node.operand):
        if isinstance(child, Node):
            lines.extend(render_tree_node(child, indent + 2, show_line))
    for child_list in (node.stmts, node.args, node.params):
        for child in child_list:
            lines.extend(render_tree_node(child, indent + 2, show_line))
    return lines


def print_tokens(tokens) -> None:
    for tok in tokens:
        if tok.kind == TK_EOF:
            text = "<eof>"
        elif tok.kind in (TK_PUNCT,):
            text = tok.sval
        elif tok.sval:
            text = tok.sval
        else:
            text = str(tok.val)
        print(f"line {tok.line:<3} {tok.kind:<8} {text}")


def load_source(path: str, use_preprocess: bool) -> str:
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    return preprocess(source, path) if use_preprocess else source


def main() -> None:
    ap = argparse.ArgumentParser(description="Show tokens or parser AST for a C subset source file.")
    ap.add_argument("file", help="input C source file")
    ap.add_argument("--tokens", action="store_true", help="print token stream instead of AST")
    ap.add_argument("--format", choices=("sexp", "tree", "json", "dot"), default="sexp", help="AST output format")
    ap.add_argument("--show-line", action="store_true", help="include source line numbers in AST output")
    ap.add_argument("--no-preprocess", action="store_true", help="skip the scaffold preprocessor")
    args = ap.parse_args()

    source = load_source(args.file, not args.no_preprocess)
    tokens = tokenize(source, args.file)

    if args.tokens:
        print_tokens(tokens)
        return

    program = parse(tokens)
    if args.format == "sexp":
        print(render_sexp(program_to_sexp(program, args.show_line)))
    elif args.format == "tree":
        print("Program")
        for node in program:
            print("\n".join(render_tree_node(node, 2, args.show_line)))
    elif args.format == "dot":
        print(render_dot(program, args.show_line))
    else:
        print(json.dumps([node_to_dict(node, args.show_line) for node in program], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(1)
