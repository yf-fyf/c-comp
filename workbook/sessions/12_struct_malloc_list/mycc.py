"""
コマ12: 構造体とヒープ（struct / . / -> / sizeof / malloc / 連結リスト。学生用スケルトン）

目標: struct のレイアウトを管理してメンバアクセスをコード生成し、
      sizeof(struct タグ) で求めたサイズを malloc に渡して連結リストを動かす。

実行方法:
    python3 sessions/12_struct_malloc_list/mycc.py input.c \
        | riscv64-linux-gnu-gcc -x assembler -static - -o out
    qemu-riscv64 ./out; echo $?
"""

import importlib.util
import re
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '11_expr_walk_libc' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session11', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)


Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen13(prev.Codegen12):
    def __init__(self, struct_defs: dict[str, dict]) -> None:
        super().__init__()
        self._struct_defs = struct_defs

    @classmethod
    def parse_struct_defs(cls, source: str) -> dict[str, dict]:
        defs: dict[str, dict] = {}
        pattern = re.compile(r'struct\s+([a-zA-Z_]\w*)\s*\{')
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
            struct_name = f'struct {tag}'
            fields = cls.parse_field_decls(source[body_start + 1:body_end])
            if not fields:
                pos = body_end + 1
                continue
            # 自然整列: 各フィールドは自身の整列へ切り上げ、
            # struct 全体のサイズは最大フィールド整列の倍数へ切り上げ
            field_map: dict[str, tuple[int, str]] = {}
            offset = 0
            struct_align = 1
            for fname, fty in fields:
                fsz = cls.size_of_ty_str(fty, defs)
                align = cls.align_of_ty_str(fty)
                struct_align = max(struct_align, align)
                offset = ((offset + align - 1) // align) * align
                field_map[fname] = (offset, fty)
                offset += fsz
            total_size = ((offset + struct_align - 1) // struct_align) * struct_align
            defs[f'struct {tag}'] = {'size': total_size, 'align': struct_align, 'fields': field_map}
            pos = body_end + 1
        return defs

    @staticmethod
    def parse_field_decls(body: str) -> list[tuple[str, str]]:
        fields: list[tuple[str, str]] = []
        type_keywords = {'int', 'char', 'void', 'struct'}
        for part in body.split(';'):
            part = part.strip()
            if not part:
                continue
            part = part.split('//')[0].strip()
            if not part:
                continue
            tokens = re.findall(r'[a-zA-Z_]\w*|\*', part)
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
            fields.append((tokens[name_idx], ' '.join(tokens[:name_idx]).replace(' *', '*')))
        return fields

    @classmethod
    def size_of_ty_str(cls, ty_str: str, struct_defs: dict[str, dict] | None = None) -> int:
        if ty_str.endswith('*'):
            return 8
        if ty_str == 'char':
            return 1
        if ty_str == 'void':
            return 1
        if ty_str.startswith('struct ') and struct_defs and ty_str in struct_defs:
            return struct_defs[ty_str]['size']
        return 4

    @staticmethod
    def align_of_ty_str(ty_str: str) -> int:
        # フィールドは int / char / ポインタのみ（struct 値のフィールドはない）
        if ty_str.endswith('*'):
            return 8
        if ty_str == 'char':
            return 1
        return 4

    @staticmethod
    def is_struct_ty_str(ty_str: str, struct_defs: dict[str, dict]) -> bool:
        return ty_str.startswith('struct ') and not ty_str.endswith('*') and ty_str in struct_defs

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
        #       コマ11 版は次の形だった。size_of_ty_str に self._struct_defs を足す。
        #           sz = self.align_to(self.size_of_ty_str(ty_str), 8)
        #           self._stack_offset += sz
        #           self._locals[name] = (-(16 + self._stack_offset), ty_str)
        raise NotImplementedError("alloc_local を実装してください")

    def _scale_index(self, elem_ty: str) -> None:
        # TODO: struct へのポインタでは self._struct_defs を渡して要素サイズを計算する。
        #       コマ11 版は次の形だった。
        #           sz = self.size_of_ty_str(elem_ty)
        #           if sz != 1:
        #               self.emit(f'  li a1, {sz}')
        #               self.emit('  mul a0, a0, a1')
        raise NotImplementedError("_scale_index を実装してください")

    def _load_ty(self, ty_str: str) -> None:
        # TODO: self._struct_defs を渡してサイズを求め、
        #       struct 型はロードせずアドレスのまま扱う（is_struct_ty_str で判定）。
        #       コマ11 版は次の形だった。
        #           sz = self.size_of_ty_str(ty_str)
        #           if sz == 1:
        #               self.emit('  lb a0, 0(a0)')
        #           elif sz == 4:
        #               self.emit('  lw a0, 0(a0)')
        #           else:
        #               self.emit('  ld a0, 0(a0)')
        raise NotImplementedError("_load_ty を実装してください")

    def _store_ty(self, ty_str: str) -> None:
        # TODO: struct のサイズを引けるよう self._struct_defs を渡す。
        #       コマ11 版は次の形だった。
        #           sz = self.size_of_ty_str(ty_str)
        #           if sz == 1:
        #               self.emit('  sb a0, 0(a1)')
        #           elif sz == 4:
        #               self.emit('  sw a0, 0(a1)')
        #           else:
        #               self.emit('  sd a0, 0(a1)')
        raise NotImplementedError("_store_ty を実装してください")

    def type_of_expr_Member(self, node: Node) -> str:
        # TODO: Member は左辺値型と同じ型を返す。
        raise NotImplementedError("type_of_expr_Member を実装してください")

    def type_of_expr_SizeofType(self, node: Node) -> str:
        # TODO: sizeof(type) の型は int。
        raise NotImplementedError("type_of_expr_SizeofType を実装してください")

    def type_of_expr_Neg(self, node: Node) -> str:
        return 'int'

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
            case 'Mul' | 'Div' | 'Mod' | 'Eq' | 'Ne' | 'Lt' | 'Le':
                return 'int'
            case 'SizeofType':
                return self.type_of_expr_SizeofType(node)
            case 'PreInc' | 'PreDec':
                return self._type_of_lval(node.operand)
            case 'Cond':
                return self._type_of_expr(node.then)
            case 'Neg':
                return self.type_of_expr_Neg(node)
            case _:
                raise RuntimeError(f'type_of_expr: この回で未対応の式です (kind={node.kind!r})')

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

    def codegen_SizeofType(self, node: Node) -> None:
        # TODO: node.ty_str のサイズを self._struct_defs 込みで計算し、
        #       li a0, <size> を出力する。
        raise NotImplementedError("codegen_SizeofType を実装してください")

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
            case 'SizeofType':
                self.codegen_SizeofType(node)
            case 'Cond':
                self.codegen_Cond(node)
            case 'PreInc':
                self.codegen_PreInc(node)
            case 'PreDec':
                self.codegen_PreDec(node)
            case _:
                raise RuntimeError(f'codegen: この回で未対応の式です (kind={node.kind!r})')

    def collect_strings_expr_Member(self, node: Node) -> None:
        # TODO: Member の operand を走査する。
        raise NotImplementedError("collect_strings_expr_Member を実装してください")

    def collect_strings_expr(self, node: Node) -> None:
        match node.kind:
            case 'Member':
                self.collect_strings_expr_Member(node)
            case 'Str':
                self.collect_strings_expr_Str(node)
            case 'Num' | 'Var' | 'SizeofType':
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


Codegen = Codegen13


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/12_struct_malloc_list/mycc.py <source.c>",
              file=sys.stderr)
        sys.exit(1)
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source, filename)
    struct_defs = Codegen13.parse_struct_defs(source)
    tokens = tokenize(source, filename)
    prog = parse(tokens)
    cg = Codegen13(struct_defs)
    for node in prog:
        if node.kind == 'FuncDef':
            cg.collect_strings_stmt(node.body)
    cg.emit_data_section()
    cg.emit('  .text')
    for node in prog:
        cg.gen_func(node)
    sys.stdout.write(cg.output())


if __name__ == '__main__':
    main()
