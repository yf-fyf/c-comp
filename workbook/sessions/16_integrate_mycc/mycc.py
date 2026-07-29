"""
コマ 16: コードレビュー・リファクタリング用（koma15 と同じ完成形）

目標: koma15 までのコードを持ち寄り、相互レビューとリファクタリングを行う。
      このファイルは koma15 完成形（全 TODO 実装済み・複数ファイル対応済み）。

実行方法:
    python3 sessions/16_integrate_mycc/mycc.py main.c lib.c \
        | riscv64-linux-gnu-gcc -x assembler -static - -o out
    qemu-riscv64 ./out; echo $?
"""

import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scaffold'))

from ast_def import *
from lexer import preprocess, tokenize
from parser import parse, Parser


def register_typedef_names(source: str) -> set[str]:
    names: set[str] = set()
    pattern = re.compile(r'\btypedef\b')
    pos = 0
    while True:
        m = pattern.search(source, pos)
        if not m:
            break
        start = m.end()
        brace = 0
        semi = start
        found = False
        i = start
        while i < len(source) and not found:
            c = source[i]
            if c == '{':
                brace += 1
            elif c == '}':
                brace -= 1
            elif c == ';' and brace == 0:
                semi = i
                found = True
            i += 1
        if not found:
            break
        text = source[start:semi]
        words = re.findall(r'[a-zA-Z_]\w*|\*', text)
        if words:
            for w in reversed(words):
                if w != '*':
                    name = w
                    break
            if name and name not in ('struct', 'int', 'char', 'void', 'unsigned', 'long', 'short'):
                names.add(name)
        pos = semi + 1
    return names


def parse_struct_defs(source: str) -> dict[str, dict]:
    defs: dict[str, dict] = {}
    pattern = re.compile(r'(?:typedef\s+)?struct\s+([a-zA-Z_]\w*)?\s*\{')
    pos = 0
    while True:
        m = pattern.search(source, pos)
        if not m:
            break
        tag = m.group(1)
        body_start = m.end() - 1
        brace = 0
        body_end = body_start
        i = body_start
        while i < len(source):
            if source[i] == '{':
                brace += 1
            elif source[i] == '}':
                brace -= 1
                if brace == 0:
                    body_end = i
                    break
            i += 1
        if i >= len(source):
            break
        body_text = source[body_start + 1:body_end]
        after = source[body_end + 1:]
        name_match = re.search(r'([a-zA-Z_]\w*)\s*;', after)
        typedef_name = name_match.group(1) if name_match else None
        if typedef_name:
            struct_name = typedef_name
        elif tag:
            struct_name = f'struct {tag}'
        else:
            pos = body_end + 1
            continue
        fields = parse_field_decls(body_text)
        if not fields:
            pos = body_end + 1
            continue
        field_map: dict[str, tuple[int, str]] = {}
        offset = 0
        for fname, fty in fields:
            fsz = size_of_ty_str(fty, defs)
            align = min(fsz, 8)
            offset = ((offset + align - 1) // align) * align
            field_map[fname] = (offset, fty)
            offset += fsz
        total_size = ((offset + 7) // 8) * 8
        defs[struct_name] = {'size': total_size, 'fields': field_map}
        if typedef_name and tag:
            tag_name = f'struct {tag}'
            if tag_name not in defs:
                defs[tag_name] = defs[struct_name]
        pos = body_end + 1
    return defs


def parse_field_decls(body: str) -> list[tuple[str, str]]:
    """struct body 内のフィールド宣言をパース: [(name, ty_str), ...]"""
    fields: list[tuple[str, str]] = []
    type_keywords = {'int', 'char', 'void', 'struct', 'unsigned', 'long', 'short'}
    parts = body.split(';')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        part = part.split('//')[0].strip()
        part = part.split('/*')[0].strip()
        if not part:
            continue
        tokens = re.findall(r'[a-zA-Z_]\w*|\[[^\]]+\]|\*', part)
        if len(tokens) < 2:
            continue
        name_idx = -1
        for i in range(len(tokens) - 1, -1, -1):
            tok = tokens[i]
            if re.match(r'^[a-zA-Z_]', tok) and tok not in type_keywords:
                name_idx = i
                break
        if name_idx < 0:
            continue
        name_str = tokens[name_idx]
        idx = name_idx + 1
        while idx < len(tokens) and re.match(r'^\[', tokens[idx]):
            name_str += tokens[idx]
            idx += 1
        type_str = ' '.join(tokens[:name_idx])
        fields.append((name_str, type_str))
    return fields


def size_of_ty_str(ty_str: str, struct_defs: dict[str, dict] = None) -> int:
    if ty_str.endswith('*'):
        return 8
    m = re.match(r'(.+)\[(\d+)\]', ty_str)
    if m:
        return size_of_ty_str(m.group(1), struct_defs) * int(m.group(2))
    if ty_str == 'char':
        return 1
    if ty_str == 'void':
        return 1
    if ty_str.startswith('struct ') and struct_defs:
        tag = ty_str[7:]
        if tag in struct_defs:
            return struct_defs[tag]['size']
    if struct_defs and ty_str in struct_defs:
        return struct_defs[ty_str]['size']
    return 4


def is_ptr_ty_str(ty_str: str) -> bool:
    return ty_str.endswith('*')


def is_array_ty_str(ty_str: str) -> bool:
    return '[' in ty_str


def is_struct_ty_str(ty_str: str, struct_defs: dict[str, dict]) -> bool:
    if ty_str.startswith('struct '):
        return ty_str[7:] in struct_defs
    return ty_str in struct_defs


def elem_ty_str(ty_str: str) -> str:
    if ty_str.endswith('*'):
        return ty_str[:-1]
    m = re.match(r'(.+)\[(\d+)\]', ty_str)
    if m:
        return m.group(1)
    return ty_str


def field_ty(struct_name: str, field_name: str, struct_defs: dict[str, dict], line: int) -> str:
    if struct_name not in struct_defs:
        raise RuntimeError(f"[line {line}] 構造体型ではありません: '{struct_name}'")
    if field_name not in struct_defs[struct_name]['fields']:
        raise RuntimeError(f"[line {line}] 構造体にフィールド '{field_name}' がありません")
    return struct_defs[struct_name]['fields'][field_name][1]


def field_offset(struct_name: str, field_name: str, struct_defs: dict[str, dict], line: int) -> int:
    if struct_name not in struct_defs:
        raise RuntimeError(f"[line {line}] 構造体型ではありません: '{struct_name}'")
    if field_name not in struct_defs[struct_name]['fields']:
        raise RuntimeError(f"[line {line}] 構造体にフィールド '{field_name}' がありません")
    return struct_defs[struct_name]['fields'][field_name][0]


class Codegen:
    def __init__(self, struct_defs: dict[str, dict]) -> None:
        self._out: list[str] = []
        self._locals: dict[str, tuple[int, str]] = {}
        self._stack_offset: int = 0
        self._label_n: int = 0
        self._ret_label: str = ''
        self._break_stack: list[str] = []
        self._cont_stack: list[str] = []
        self._strings: dict[str, str] = {}
        self._str_label_n: int = 0
        self._struct_defs = struct_defs
        # グローバル変数: name -> (ty_str, init_value or None)
        self._globals: dict[str, tuple[str, int | None]] = {}
        # スタックに積んでいる一時値の個数（1個 8 バイト）。call 直前の sp の
        # アラインメント判定に使う（_gen_call を参照）
        self._depth: int = 0

    def emit(self, line: str) -> None:
        self._out.append(line)

    def output(self) -> str:
        return '\n'.join(self._out) + '\n'

    def new_label(self) -> str:
        self._label_n += 1
        return f'.L{self._label_n}'

    # ---- 文字列 ----

    def _intern(self, value: str) -> str:
        if value in self._strings:
            return self._strings[value]
        self._str_label_n += 1
        label = f'.LC{self._str_label_n}'
        self._strings[value] = label
        return label

    def collect_strings_stmt(self, node: Node) -> None:
        match node.kind:
            case 'Str':
                self._intern(node.sval)
            case 'Var' | 'Num' | 'Break' | 'Continue':
                pass
            case 'Decl':
                if node.init_expr is not None:
                    self.collect_strings_expr(node.init_expr)
            case 'ExprStmt' | 'Return':
                if node.operand is not None:
                    self.collect_strings_expr(node.operand)
            case 'Block':
                for stmt in node.stmts:
                    self.collect_strings_stmt(stmt)
            case 'If':
                self.collect_strings_expr(node.cond)
                self.collect_strings_stmt(node.then)
                if node.else_ is not None:
                    self.collect_strings_stmt(node.else_)
            case 'While':
                self.collect_strings_expr(node.cond)
                self.collect_strings_stmt(node.body)
            case 'For':
                if node.init is not None:
                    self.collect_strings_expr(node.init)
                if node.cond is not None:
                    self.collect_strings_expr(node.cond)
                if node.step is not None:
                    self.collect_strings_expr(node.step)
                self.collect_strings_stmt(node.body)
            case _:
                pass

    def collect_strings_expr(self, node: Node) -> None:
        match node.kind:
            case 'Str':
                self._intern(node.sval)
            case 'Num' | 'Var' | 'SizeofType':
                pass
            case 'Neg' | 'Not' | 'BitNot' | 'Addr' | 'Deref' | 'SizeofExpr' | 'Member':
                self.collect_strings_expr(node.operand)
            case 'Assign' | 'Binary' | 'Index':
                self.collect_strings_expr(node.lhs)
                self.collect_strings_expr(node.rhs)
            case 'Call':
                for arg in node.args:
                    self.collect_strings_expr(arg)
            case _:
                pass

    # ---- グローバル変数収集 ----

    def _const_int_value(self, node: Node | None) -> int | None:
        """整数定数式から値を取り出す。定数式でなければ None"""
        if node is None:
            return None
        match node.kind:
            case 'Num':
                return node.val
            case 'Neg':
                v = self._const_int_value(node.operand)
                return -v if v is not None else None
            case _:
                return None

    def collect_globals(self, prog: list[Node]) -> None:
        for node in prog:
            if node.kind == 'Decl':
                self._globals[node.name] = (node.ty_str or 'int', self._const_int_value(node.init_expr))

    def collect_all_strings(self, prog: list[Node]) -> None:
        for node in prog:
            match node.kind:
                case 'FuncDef':
                    self.collect_strings_stmt(node.body)
                case 'Decl':
                    if node.init_expr is not None:
                        self.collect_strings_expr(node.init_expr)
                case _:
                    pass

    def emit_data_section(self) -> None:
        has_init = any(v is not None for _, (_, v) in self._globals.items())
        if not self._strings and not has_init:
            return
        self.emit('  .data')
        for value, label in sorted(self._strings.items(), key=lambda x: x[1]):
            self.emit(f'{label}:')
            for ch in value:
                self.emit(f'  .byte {ord(ch)}')
            self.emit('  .byte 0')
        for name, (ty, val) in self._globals.items():
            if val is not None:
                self.emit(f'  .globl {name}')
                self.emit(f'{name}:')
                sz = size_of_ty_str(ty, self._struct_defs)
                if sz == 1:
                    self.emit(f'  .byte {val}')
                elif sz == 4:
                    self.emit(f'  .word {val}')
                else:
                    self.emit(f'  .dword {val}')

    def emit_bss_section(self) -> None:
        has_uninit = any(v is None for _, (_, v) in self._globals.items())
        if not has_uninit:
            return
        self.emit('  .bss')
        for name, (ty, val) in self._globals.items():
            if val is None:
                self.emit(f'  .globl {name}')
                self.emit(f'{name}:')
                sz = self._align_to(size_of_ty_str(ty, self._struct_defs), 8)
                self.emit(f'  .zero {sz}')

    # ---- 変数管理 ----

    @staticmethod
    def _align_to(n: int, align: int) -> int:
        return ((n + align - 1) // align) * align

    def alloc_local(self, name: str, ty_str: str) -> None:
        sz = self._align_to(size_of_ty_str(ty_str, self._struct_defs), 8)
        self._stack_offset += sz
        self._locals[name] = (-(16 + self._stack_offset), ty_str)

    def lookup_var(self, name: str, line: int) -> int:
        if name in self._locals:
            return self._locals[name][0]
        if name in self._globals:
            return 0  # global: address loaded via la, offset unused
        raise RuntimeError(f"[line {line}] 未定義の変数: '{name}'")

    def _is_local(self, name: str) -> bool:
        return name in self._locals

    def lookup_var_ty(self, name: str, line: int) -> str:
        if name in self._locals:
            return self._locals[name][1]
        if name in self._globals:
            return self._globals[name][0]
        raise RuntimeError(f"[line {line}] 未定義の変数 (type_of): '{name}'")

    # ---- 型推論 ----

    def _type_of_expr(self, node: Node) -> str:
        match node.kind:
            case 'Num':
                return 'int'
            case 'Str':
                return 'char*'
            case 'Var':
                return self.lookup_var_ty(node.name, node.line)
            case 'Addr':
                return self._type_of_lval(node.operand) + '*'
            case 'Deref':
                inner = self._type_of_expr(node.operand)
                if inner.endswith('*'):
                    return inner[:-1]
                return 'int'
            case 'Index' | 'Member':
                return self._type_of_lval(node)
            case 'Assign':
                return self._type_of_lval(node.lhs)
            case 'Call':
                return 'int'
            case 'SizeofType' | 'SizeofExpr':
                return 'int'
            case 'Neg' | 'Not' | 'BitNot':
                return 'int'
            case 'Add':
                lt = self._type_of_expr(node.lhs)
                rt = self._type_of_expr(node.rhs)
                if lt.endswith('*'):
                    return lt
                if rt.endswith('*'):
                    return rt
                return 'int'
            case 'Sub':
                lt = self._type_of_expr(node.lhs)
                if lt.endswith('*'):
                    return lt
                return 'int'
            case _:
                return 'int'

    def _type_of_lval(self, node: Node) -> str:
        match node.kind:
            case 'Var':
                return self.lookup_var_ty(node.name, node.line)
            case 'Deref':
                inner = self._type_of_expr(node.operand)
                if inner.endswith('*'):
                    return inner[:-1]
                return 'int'
            case 'Index':
                base_ty = self._type_of_expr(node.lhs)
                if base_ty.endswith('*'):
                    return base_ty[:-1]
                if is_array_ty_str(base_ty):
                    return elem_ty_str(base_ty)
                return 'int'
            case 'Member':
                struct_ty = self._member_struct_type(node)
                return field_ty(struct_ty, node.name, self._struct_defs, node.line)
            case _:
                return 'int'

    def _member_struct_type(self, node: Node) -> str:
        if node.is_arrow:
            ptr_ty = self._type_of_expr(node.operand)
            if ptr_ty.endswith('*'):
                inner = ptr_ty[:-1]
                if is_struct_ty_str(inner, self._struct_defs):
                    return inner
                if inner.startswith('struct '):
                    return inner[7:]
            raise RuntimeError(f"[line {node.line}] -> の対象が構造体ポインタではありません")
        else:
            lv_ty = self._type_of_lval(node.operand)
            if is_struct_ty_str(lv_ty, self._struct_defs):
                return lv_ty
            if lv_ty.startswith('struct ') and lv_ty[7:] in self._struct_defs:
                return lv_ty[7:]
            raise RuntimeError(f"[line {node.line}] . の対象が構造体ではありません")

    def _load_ty(self, ty_str: str) -> None:
        if is_array_ty_str(ty_str):
            return
        if is_struct_ty_str(ty_str, self._struct_defs):
            return
        sz = size_of_ty_str(ty_str, self._struct_defs)
        if sz == 1:
            self.emit('  lb a0, 0(a0)')
        elif sz == 4:
            self.emit('  lw a0, 0(a0)')
        else:
            self.emit('  ld a0, 0(a0)')

    def _store_ty(self, ty_str: str) -> None:
        sz = size_of_ty_str(ty_str, self._struct_defs)
        if sz == 1:
            self.emit('  sb a0, 0(a1)')
        elif sz == 4:
            self.emit('  sw a0, 0(a1)')
        else:
            self.emit('  sd a0, 0(a1)')

    def _scale_index(self, elem_ty: str) -> None:
        sz = size_of_ty_str(elem_ty, self._struct_defs)
        if sz != 1:
            self.emit(f'  li a1, {sz}')
            self.emit('  mul a0, a0, a1')

    def _push_a0(self) -> None:
        self.emit('  addi sp, sp, -8')
        self.emit('  sd a0, 0(sp)')
        self._depth += 1

    def _pop_into(self, reg: str) -> None:
        self.emit(f'  ld {reg}, 0(sp)')
        self.emit('  addi sp, sp, 8')
        self._depth -= 1

    # ---- 左辺値 ----

    def codegen_lval(self, node: Node) -> None:
        match node.kind:
            case 'Var':
                if self._is_local(node.name):
                    offset = self.lookup_var(node.name, node.line)
                    self.emit(f'  addi a0, s0, {offset}')
                else:
                    self.emit(f'  la a0, {node.name}')
            case 'Deref':
                self.codegen(node.operand)
            case 'Index':
                base_ty = self._type_of_expr(node.lhs)
                if base_ty.endswith('*'):
                    elem_ty = base_ty[:-1]
                elif is_array_ty_str(base_ty):
                    elem_ty = elem_ty_str(base_ty)
                else:
                    elem_ty = 'int'
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._scale_index(elem_ty)
                self._pop_into('a1')
                self.emit('  add a0, a1, a0')
            case 'Member':
                struct_name = self._member_struct_type(node)
                offset = field_offset(struct_name, node.name, self._struct_defs, node.line)
                if node.is_arrow:
                    self.codegen(node.operand)
                else:
                    self.codegen_lval(node.operand)
                if offset != 0:
                    self.emit(f'  addi a0, a0, {offset}')
            case _:
                raise RuntimeError(f"lvalue でない式です (kind={node.kind!r})")

    # ---- 式 ----

    def codegen(self, node: Node) -> None:
        match node.kind:
            case 'Num':
                self.emit(f'  li a0, {node.val}')
            case 'Str':
                label = self._intern(node.sval)
                self.emit(f'  la a0, {label}')
            case 'Var':
                self.codegen_lval(node)
                ty = self._type_of_expr(node)
                self._load_ty(ty)
            case 'Addr':
                self.codegen_lval(node.operand)
            case 'Deref':
                ty = self._type_of_expr(node.operand)
                self.codegen(node.operand)
                if ty.endswith('*'):
                    self._load_ty(ty[:-1])
                else:
                    self._load_ty('int')
            case 'Index' | 'Member':
                self.codegen_lval(node)
                ty = self._type_of_expr(node)
                self._load_ty(ty)
            case 'Assign':
                ty = self._type_of_lval(node.lhs)
                self.codegen_lval(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self._store_ty(ty)
            case 'SizeofType':
                sz = size_of_ty_str(node.ty_str, self._struct_defs)
                self.emit(f'  li a0, {sz}')
            case 'SizeofExpr':
                sz = size_of_ty_str(self._type_of_expr(node.operand), self._struct_defs)
                self.emit(f'  li a0, {sz}')
            case 'Neg':
                self.codegen(node.operand)
                self.emit('  neg a0, a0')
            case 'Not':
                self.codegen(node.operand)
                self.emit('  seqz a0, a0')
            case 'BitNot':
                self.codegen(node.operand)
                self.emit('  not a0, a0')
            case 'Call':
                self._gen_call(node.name, node.args)
            case 'Add':
                lt = self._type_of_expr(node.lhs)
                rt = self._type_of_expr(node.rhs)
                if is_ptr_ty_str(lt) or is_ptr_ty_str(rt):
                    ptr_expr, int_expr, ptr_ty = (
                        (node.lhs, node.rhs, lt) if is_ptr_ty_str(lt)
                        else (node.rhs, node.lhs, rt))
                    elem_ty = elem_ty_str(ptr_ty)
                    self.codegen(ptr_expr)
                    self._push_a0()
                    self.codegen(int_expr)
                    self._scale_index(elem_ty)
                    self._pop_into('a1')
                    self.emit('  add a0, a1, a0')
                else:
                    self.codegen(node.lhs)
                    self._push_a0()
                    self.codegen(node.rhs)
                    self._pop_into('a1')
                    self.emit('  add a0, a1, a0')
            case 'Sub':
                lt = self._type_of_expr(node.lhs)
                if is_ptr_ty_str(lt):
                    elem_ty = elem_ty_str(lt)
                    self.codegen(node.lhs)
                    self._push_a0()
                    self.codegen(node.rhs)
                    self._scale_index(elem_ty)
                    self._pop_into('a1')
                    self.emit('  sub a0, a1, a0')
                else:
                    self.codegen(node.lhs)
                    self._push_a0()
                    self.codegen(node.rhs)
                    self._pop_into('a1')
                    self.emit('  sub a0, a1, a0')
            case 'Mul' | 'Div' | 'Mod':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                op_map = {'Mul': 'mul', 'Div': 'div', 'Mod': 'rem'}
                self.emit(f'  {op_map[node.kind]} a0, a1, a0')
            case 'Eq':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self.emit('  sub a0, a1, a0')
                self.emit('  seqz a0, a0')
            case 'Ne':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self.emit('  sub a0, a1, a0')
                self.emit('  snez a0, a0')
            case 'Lt':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self.emit('  slt a0, a1, a0')
            case 'Le':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self.emit('  slt a0, a0, a1')
                self.emit('  xori a0, a0, 1')
            # 追加の二項演算子
            case 'And':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self.emit('  snez a1, a1')
                self.emit('  snez a0, a0')
                self.emit('  and a0, a1, a0')
            case 'Or':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self.emit('  or a0, a1, a0')
                self.emit('  snez a0, a0')
            case 'BitAnd':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self.emit('  and a0, a1, a0')
            case 'BitOr':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self.emit('  or a0, a1, a0')
            case 'BitXor':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self.emit('  xor a0, a1, a0')
            case 'Shl':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self.emit('  sll a0, a1, a0')
            case 'Shr':
                self.codegen(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                self.emit('  sra a0, a1, a0')
            case _:
                raise RuntimeError(f'codegen: コマ16で未対応の式です (kind={node.kind!r})')

    def _gen_call(self, name: str, args: list[Node]) -> None:
        n = len(args)
        for arg in args:
            self.codegen(arg)
            self._push_a0()
        for i in range(n):
            self.emit(f'  ld a{i}, {(n - 1 - i) * 8}(sp)')
        if n:
            self.emit(f'  addi sp, sp, {n * 8}')
            self._depth -= n
        # ここで sp は「呼び出しを囲む式が積んだ一時値」の分だけフレームから下がっている。
        # 一時値は 1 個 8 バイトなので、奇数個なら 16 バイト境界からずれている
        pad = 8 if self._depth % 2 else 0
        if pad:
            self.emit(f'  addi sp, sp, -{pad}')
        self.emit(f'  call {name}')
        if pad:
            self.emit(f'  addi sp, sp, {pad}')

    # ---- 文 ----

    def gen_stmt(self, node: Node) -> None:
        match node.kind:
            case 'Decl':
                if node.init_expr is not None:
                    lhs = Node('Var', name=node.name, line=node.line)
                    self.codegen(Node('Assign', lhs=lhs, rhs=node.init_expr, line=node.line))
            case 'ExprStmt':
                if node.operand is not None:
                    self.codegen(node.operand)
            case 'Return':
                if node.operand is not None:
                    self.codegen(node.operand)
                self.emit(f'  j {self._ret_label}')
            case 'Block':
                for stmt in node.stmts:
                    self.gen_stmt(stmt)
            case 'If':
                label_else = self.new_label()
                self.codegen(node.cond)
                self.emit(f'  beqz a0, {label_else}')
                self.gen_stmt(node.then)
                if node.else_ is not None:
                    label_end = self.new_label()
                    self.emit(f'  j {label_end}')
                    self.emit(f'{label_else}:')
                    self.gen_stmt(node.else_)
                    self.emit(f'{label_end}:')
                else:
                    self.emit(f'{label_else}:')
            case 'While':
                label_cond = self.new_label()
                label_end = self.new_label()
                self._break_stack.append(label_end)
                self._cont_stack.append(label_cond)
                self.emit(f'{label_cond}:')
                self.codegen(node.cond)
                self.emit(f'  beqz a0, {label_end}')
                self.gen_stmt(node.body)
                self.emit(f'  j {label_cond}')
                self.emit(f'{label_end}:')
                self._break_stack.pop()
                self._cont_stack.pop()
            case 'For':
                label_cond = self.new_label()
                label_step = self.new_label()
                label_end = self.new_label()
                self._break_stack.append(label_end)
                self._cont_stack.append(label_step)
                if node.init is not None:
                    self.codegen(node.init)
                self.emit(f'{label_cond}:')
                if node.cond is not None:
                    self.codegen(node.cond)
                    self.emit(f'  beqz a0, {label_end}')
                self.gen_stmt(node.body)
                self.emit(f'{label_step}:')
                if node.step is not None:
                    self.codegen(node.step)
                self.emit(f'  j {label_cond}')
                self.emit(f'{label_end}:')
                self._break_stack.pop()
                self._cont_stack.pop()
            case 'Break':
                self.emit(f'  j {self._break_stack[-1]}')
            case 'Continue':
                self.emit(f'  j {self._cont_stack[-1]}')
            case _:
                pass

    def collect_decls(self, node: Node) -> None:
        match node.kind:
            case 'Decl':
                self.alloc_local(node.name, node.ty_str or 'int')
            case 'Block':
                for stmt in node.stmts:
                    self.collect_decls(stmt)
            case 'If':
                self.collect_decls(node.then)
                if node.else_ is not None:
                    self.collect_decls(node.else_)
            case 'While':
                self.collect_decls(node.body)
            case 'For':
                self.collect_decls(node.body)
            case _:
                pass

    def gen_func(self, node: Node) -> None:
        if node.kind != 'FuncDef':
            return
        name = node.name
        self._depth = 0
        self._locals.clear()
        self._stack_offset = 0
        self._ret_label = self.new_label()
        self._break_stack.clear()
        self._cont_stack.clear()
        for p in node.params:
            if p.name:
                self.alloc_local(p.name, p.ty_str or 'int')
        self.collect_decls(node.body)
        frame_size = self._align_to(self._stack_offset, 16)
        self.emit(f'  .globl {name}')
        self.emit(f'{name}:')
        self.emit(f'  addi sp, sp, -{frame_size + 16}')
        self.emit(f'  sd ra, {frame_size + 8}(sp)')
        self.emit(f'  sd s0, {frame_size}(sp)')
        self.emit(f'  addi s0, sp, {frame_size + 16}')
        for i, p in enumerate(node.params):
            if p.name and i < 8 and p.name in self._locals:
                offset = self._locals[p.name][0]
                self.emit(f'  sd a{i}, {offset}(s0)')
        self.gen_stmt(node.body)
        if self._depth != 0:
            raise RuntimeError(f'push と pop の数が合っていない (depth={self._depth})')
        self.emit(f'{self._ret_label}:')
        self.emit(f'  ld s0, {frame_size}(sp)')
        self.emit(f'  ld ra, {frame_size + 8}(sp)')
        self.emit(f'  addi sp, sp, {frame_size + 16}')
        self.emit('  ret')

    def gen_program(self, prog: list[Node]) -> None:
        self.emit_data_section()
        self.emit_bss_section()
        self.emit('  .text')
        for node in prog:
            self.gen_func(node)


def parse_file(filename: str) -> tuple[list[Node], dict[str, dict]]:
    """ファイルを読み込み、前処理・型登録・パースを行って AST と struct_defs を返す。"""
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source, filename)
    typedef_names = register_typedef_names(source)
    struct_defs = parse_struct_defs(source)
    tokens = tokenize(source, filename)
    p = Parser(tokens)
    p.typedef_names.update(typedef_names)
    return p.parse_program(), struct_defs


def main():
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/16_integrate_mycc/mycc.py <source.c> [...]", file=sys.stderr)
        sys.exit(1)

    prog: list[Node] = []
    all_struct_defs: dict[str, dict] = {}

    for filename in sys.argv[1:]:
        file_prog, struct_defs = parse_file(filename)
        prog.extend(file_prog)
        all_struct_defs.update(struct_defs)

    cg = Codegen(all_struct_defs)
    cg.collect_globals(prog)
    cg.collect_all_strings(prog)
    cg.gen_program(prog)
    sys.stdout.write(cg.output())


if __name__ == '__main__':
    main()
