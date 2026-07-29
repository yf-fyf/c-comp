"""コマ 12: struct / typedef / メンバアクセス（学生用スケルトン）。"""

import importlib.util
import re
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '11_strings_printf' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session11', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

from parser import Parser

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen12(prev.Codegen11):
    def __init__(self, struct_defs: dict[str, dict]) -> None:
        super().__init__()
        self._struct_defs = struct_defs

    @classmethod
    def register_typedef_names(cls, source: str) -> set[str]:
        names: set[str] = set()
        pattern = re.compile(r'\btypedef\b')
        pos = 0
        while True:
            m = pattern.search(source, pos)
            if not m:
                break
            start = m.end()
            brace = 0
            found = False
            i = start
            semi = start
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
            words = re.findall(r'[a-zA-Z_]\w*|\*', source[start:semi])
            if words:
                name = ''
                for w in reversed(words):
                    if w != '*':
                        name = w
                        break
                if name and name not in ('struct', 'int', 'char', 'void', 'unsigned', 'long', 'short'):
                    names.add(name)
            pos = semi + 1
        return names

    @classmethod
    def parse_struct_defs(cls, source: str) -> dict[str, dict]:
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
            fields = cls.parse_field_decls(source[body_start + 1:body_end])
            if not fields:
                pos = body_end + 1
                continue
            field_map: dict[str, tuple[int, str]] = {}
            offset = 0
            for fname, fty in fields:
                fsz = cls.size_of_ty_str(fty, defs)
                align = min(fsz, 8)
                offset = ((offset + align - 1) // align) * align
                field_map[fname] = (offset, fty)
                offset += fsz
            total_size = ((offset + 7) // 8) * 8
            defs[struct_name] = {'size': total_size, 'fields': field_map}
            if typedef_name and tag:
                defs.setdefault(f'struct {tag}', defs[struct_name])
            pos = body_end + 1
        return defs

    @staticmethod
    def parse_field_decls(body: str) -> list[tuple[str, str]]:
        fields: list[tuple[str, str]] = []
        type_keywords = {'int', 'char', 'void', 'struct', 'unsigned', 'long', 'short'}
        for part in body.split(';'):
            part = part.strip()
            if not part:
                continue
            part = part.split('//')[0].strip().split('/*')[0].strip()
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
            fields.append((name_str, ' '.join(tokens[:name_idx])))
        return fields

    @classmethod
    def size_of_ty_str(cls, ty_str: str, struct_defs: dict[str, dict] | None = None) -> int:
        if ty_str.endswith('*'):
            return 8
        m = re.match(r'(.+)\[(\d+)\]', ty_str)
        if m:
            return cls.size_of_ty_str(m.group(1), struct_defs) * int(m.group(2))
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

    @staticmethod
    def is_struct_ty_str(ty_str: str, struct_defs: dict[str, dict]) -> bool:
        if ty_str.startswith('struct '):
            return ty_str[7:] in struct_defs or ty_str in struct_defs
        return ty_str in struct_defs

    @staticmethod
    def field_ty(struct_name: str, field_name: str, struct_defs: dict[str, dict], line: int) -> str:
        if struct_name not in struct_defs:
            raise RuntimeError(f"[line {line}] 構造体型ではありません: '{struct_name}'")
        fields = struct_defs[struct_name]['fields']
        if field_name not in fields:
            raise RuntimeError(f"[line {line}] 構造体にフィールド '{field_name}' がありません")
        return fields[field_name][1]

    @staticmethod
    def field_offset(struct_name: str, field_name: str, struct_defs: dict[str, dict], line: int) -> int:
        if struct_name not in struct_defs:
            raise RuntimeError(f"[line {line}] 構造体型ではありません: '{struct_name}'")
        fields = struct_defs[struct_name]['fields']
        if field_name not in fields:
            raise RuntimeError(f"[line {line}] 構造体にフィールド '{field_name}' がありません")
        return fields[field_name][0]

    def _member_struct_type(self, node: Node) -> str:
        # TODO: . と -> の違いを考慮して、Member 対象の構造体型名を返す。
        raise NotImplementedError("_member_struct_type を実装してください")

    def alloc_local(self, name: str, ty_str: str = 'int') -> None:
        # TODO: self._struct_defs を渡して struct のサイズで領域確保する。
        sz = self._align_to(self.size_of_ty_str(ty_str), 8)
        self._stack_offset += sz
        self._locals[name] = (-(16 + self._stack_offset), ty_str)

    def _scale_index(self, elem_ty: str) -> None:
        # TODO: struct 要素配列では self._struct_defs を渡して要素サイズを計算する。
        sz = self.size_of_ty_str(elem_ty)
        if sz != 1:
            self.emit(f'  li a1, {sz}')
            self.emit('  mul a0, a0, a1')

    def _load_ty(self, ty_str: str) -> None:
        # TODO: struct 型はロードせず、アドレスのまま扱う。
        if self.is_array_ty_str(ty_str):
            return
        sz = self.size_of_ty_str(ty_str)
        if sz == 1:
            self.emit('  lb a0, 0(a0)')
        elif sz == 4:
            self.emit('  lw a0, 0(a0)')
        else:
            self.emit('  ld a0, 0(a0)')

    def _store_ty(self, ty_str: str) -> None:
        # TODO: struct 型の代入に必要なコピー処理、または struct サイズ対応を検討する。
        sz = self.size_of_ty_str(ty_str)
        if sz == 1:
            self.emit('  sb a0, 0(a1)')
        elif sz == 4:
            self.emit('  sw a0, 0(a1)')
        else:
            self.emit('  sd a0, 0(a1)')

    def type_of_expr_Member(self, node: Node) -> str:
        # TODO: Member は左辺値型と同じ型を返す。
        raise NotImplementedError("type_of_expr_Member を実装してください")

    def _type_of_expr(self, node: Node) -> str:
        match node.kind:
            case 'Str':
                return self.type_of_expr_Str(node)
            case 'Num':
                return self.type_of_expr_Num(node)
            case 'Var':
                return self.type_of_expr_Var(node)
            case 'Addr':
                return self.type_of_expr_Addr(node)
            case 'Deref':
                return self.type_of_expr_Deref(node)
            case 'Index':
                return self.type_of_expr_Index(node)
            case 'Member':
                return self.type_of_expr_Member(node)
            case 'Assign':
                return self.type_of_expr_Assign(node)
            case 'Call':
                return self.type_of_expr_Call(node)
            case 'Add':
                return self.type_of_expr_Add(node)
            case 'Sub':
                return self.type_of_expr_Sub(node)
            case _:
                return 'int'

    def type_of_lval_Member(self, node: Node) -> str:
        # TODO: _member_struct_type と field_ty でメンバ型を求める。
        raise NotImplementedError("type_of_lval_Member を実装してください")

    def _type_of_lval(self, node: Node) -> str:
        match node.kind:
            case 'Var':
                return self.type_of_lval_Var(node)
            case 'Deref':
                return self.type_of_lval_Deref(node)
            case 'Index':
                return self.type_of_lval_Index(node)
            case 'Member':
                return self.type_of_lval_Member(node)
            case _:
                return 'int'

    def codegen_lval_Member(self, node: Node) -> None:
        # TODO: 対象 struct のベースアドレスに field_offset を加える。
        raise NotImplementedError("codegen_lval_Member を実装してください")

    def codegen_lval(self, node: Node) -> None:
        match node.kind:
            case 'Var':
                self.codegen_lval_Var(node)
            case 'Deref':
                self.codegen_lval_Deref(node)
            case 'Index':
                self.codegen_lval_Index(node)
            case 'Member':
                self.codegen_lval_Member(node)
            case _:
                raise RuntimeError(f"lvalue でない式です (kind={node.kind!r})")

    def codegen_Member(self, node: Node) -> None:
        # TODO: Member の左辺値アドレスを作って、メンバ型でロードする。
        raise NotImplementedError("codegen_Member を実装してください")

    def codegen(self, node: Node) -> None:
        match node.kind:
            case 'Num':
                self.codegen_Num(node)
            case 'Neg':
                self.codegen_Neg(node)
            case 'Add':
                self.codegen_Add(node)
            case 'Sub':
                self.codegen_Sub(node)
            case 'Mul':
                self.codegen_Mul(node)
            case 'Div':
                self.codegen_Div(node)
            case 'Mod':
                self.codegen_Mod(node)
            case 'Var':
                self.codegen_Var(node)
            case 'Assign':
                self.codegen_Assign(node)
            case 'Eq':
                self.codegen_Eq(node)
            case 'Ne':
                self.codegen_Ne(node)
            case 'Lt':
                self.codegen_Lt(node)
            case 'Le':
                self.codegen_Le(node)
            case 'Call':
                self.codegen_Call(node)
            case 'Addr':
                self.codegen_Addr(node)
            case 'Deref':
                self.codegen_Deref(node)
            case 'Index':
                self.codegen_Index(node)
            case 'Str':
                self.codegen_Str(node)
            case 'Member':
                self.codegen_Member(node)
            case _:
                raise RuntimeError(f'codegen: コマ12で未対応の式です (kind={node.kind!r})')

    def collect_strings_expr_Member(self, node: Node) -> None:
        # TODO: Member の operand を走査する。
        raise NotImplementedError("collect_strings_expr_Member を実装してください")

    def collect_strings_expr(self, node: Node) -> None:
        match node.kind:
            case 'Member':
                self.collect_strings_expr_Member(node)
            case 'Str':
                self.collect_strings_expr_Str(node)
            case 'Num' | 'Var':
                pass
            case 'Neg':
                self.collect_strings_expr_Neg(node)
            case 'Addr':
                self.collect_strings_expr_Addr(node)
            case 'Deref':
                self.collect_strings_expr_Deref(node)
            case 'Assign':
                self.collect_strings_expr_Assign(node)
            case 'Add':
                self.collect_strings_expr_Add(node)
            case 'Sub':
                self.collect_strings_expr_Sub(node)
            case 'Mul':
                self.collect_strings_expr_Mul(node)
            case 'Div':
                self.collect_strings_expr_Div(node)
            case 'Mod':
                self.collect_strings_expr_Mod(node)
            case 'Eq':
                self.collect_strings_expr_Eq(node)
            case 'Ne':
                self.collect_strings_expr_Ne(node)
            case 'Lt':
                self.collect_strings_expr_Lt(node)
            case 'Le':
                self.collect_strings_expr_Le(node)
            case 'Index':
                self.collect_strings_expr_Index(node)
            case 'Call':
                self.collect_strings_expr_Call(node)
            case _:
                pass


Codegen = Codegen12


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/12_struct_typedef/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source, filename)
    # TODO: typedef_names = Codegen12.register_typedef_names(source)
    # TODO: struct_defs = Codegen12.parse_struct_defs(source)
    tokens = tokenize(source, filename)
    # TODO: Parser(tokens) を使い、typedef_names を登録して parse_program() する。
    # p = Parser(tokens)
    # p.typedef_names.update(typedef_names)
    # prog = p.parse_program()
    prog = parse(tokens)
    cg = Codegen12({})
    # TODO: 収集した struct_defs を Codegen12 に渡す。
    # TODO: 文字列収集と emit_data_section() を .text より前に呼ぶ。
    cg.emit('  .text')
    for node in prog:
        cg.gen_func(node)
    sys.stdout.write(cg.output())


if __name__ == '__main__':
    main()
