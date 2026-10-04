"""コマ 8: 型検査の導入（学生用スケルトン）。int / char / ポインタを型サイズで扱う。"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '07_lvalue_rvalue' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session07', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen08(prev.Codegen07):
    @classmethod
    def size_of_ty_str(cls, ty_str: str) -> int:
        if ty_str.endswith('*'):
            return 8
        if ty_str == 'char':
            return 1
        if ty_str == 'void':
            return 1
        return 4

    @staticmethod
    def is_ptr_ty_str(ty_str: str) -> bool:
        return ty_str.endswith('*')

    @staticmethod
    def elem_ty_str(ty_str: str) -> str:
        if ty_str.endswith('*'):
            return ty_str[:-1]
        return ty_str

    def __init__(self) -> None:
        super().__init__()
        self._locals: dict[str, tuple[int, str]] = {}
        self._function_returns: dict[str, str] = {}
        self._function_params: dict[str, list[str]] = {}
        self._return_ty = 'int'

    def collect_function_returns(self, prog: list[Node]) -> None:
        # 提供済み: 宣言・定義の戻り値型と固定引数型をコード生成前に集める。
        # 再宣言の整合性や宣言の出現順を完全に検査する処理ではない。
        self._function_returns.clear()
        self._function_params.clear()
        for node in prog:
            if node.kind in ('FuncProto', 'FuncDef'):
                self._function_returns[node.name] = node.ty_str or 'int'
                self._function_params[node.name] = [p.ty_str or 'int' for p in node.params]

    def alloc_local(self, name: str, ty_str: str = 'int') -> None:
        sz = self.align_to(self.size_of_ty_str(ty_str), 8)
        self._stack_offset += sz
        self._locals[name] = (-(16 + self._stack_offset), ty_str)

    def lookup_var(self, name: str, line: int) -> int:
        if name in self._locals:
            return self._locals[name][0]
        raise RuntimeError(f"[line {line}] 未定義の変数: '{name}'")

    def lookup_local_ty(self, name: str, line: int) -> str:
        if name in self._locals:
            return self._locals[name][1]
        raise RuntimeError(f"[line {line}] 未定義の変数 (type_of): '{name}'")

    def _type_of_expr(self, node: Node) -> str:
        match node.kind:
            case 'Num':
                return self.type_of_expr_Num(node)
            case 'Var':
                return self.type_of_expr_Var(node)
            case 'Addr':
                return self.type_of_expr_Addr(node)
            case 'Deref':
                return self.type_of_expr_Deref(node)
            case 'Assign':
                return self.type_of_expr_Assign(node)
            case 'Call':
                return self.type_of_expr_Call(node)
            case 'Cond':
                return self.type_of_expr_Cond(node)
            case _:
                return 'int'

    def type_of_expr_Num(self, node: Node) -> str:
        # TODO: 数値リテラルの型を返す。
        raise NotImplementedError("type_of_expr_Num を実装してください")

    def type_of_expr_Var(self, node: Node) -> str:
        # TODO: ローカル変数表から型を取得する。
        raise NotImplementedError("type_of_expr_Var を実装してください")

    def type_of_expr_Addr(self, node: Node) -> str:
        # TODO: 左辺値の型に * を付ける。
        raise NotImplementedError("type_of_expr_Addr を実装してください")

    def type_of_expr_Deref(self, node: Node) -> str:
        # TODO: operand の型から要素型を取り出す。
        raise NotImplementedError("type_of_expr_Deref を実装してください")

    def type_of_expr_Assign(self, node: Node) -> str:
        # TODO: 代入式は左辺値の型を返す。
        raise NotImplementedError("type_of_expr_Assign を実装してください")

    def type_of_expr_Call(self, node: Node) -> str:
        # TODO: self._function_returns から node.name の戻り値型を取得する。
        # 表にない名前は従来どおり int とする（未宣言関数の診断は保証範囲外）。
        raise NotImplementedError("type_of_expr_Call を実装してください")

    def type_of_expr_Cond(self, node: Node) -> str:
        # 提供済み: 条件式は、実行時に選ぶ腕ではなく両腕の型から決める。
        lt = self._type_of_expr(node.then)
        rt = self._type_of_expr(node.else_)
        if lt in ('int', 'char') and rt in ('int', 'char'):
            return 'int'
        if lt == rt:
            return lt
        if lt.endswith('*') and rt.endswith('*') and 'void*' in (lt, rt):
            return 'void*'
        if lt.endswith('*') and node.else_.kind == 'Num' and node.else_.val == 0:
            return lt
        if rt.endswith('*') and node.then.kind == 'Num' and node.then.val == 0:
            return rt
        # 型規則全体の診断は発展Q1。ここでは共通型を決められない組合せだけ拒否する。
        raise RuntimeError(f"[line {node.line}] 条件式の両腕の型が対応しません: {lt}, {rt}")

    def _type_of_lval(self, node: Node) -> str:
        match node.kind:
            case 'Var':
                return self.type_of_lval_Var(node)
            case 'Deref':
                return self.type_of_lval_Deref(node)
            case _:
                return 'int'

    def type_of_lval_Var(self, node: Node) -> str:
        # TODO: ローカル変数表から型を取得する。
        raise NotImplementedError("type_of_lval_Var を実装してください")

    def type_of_lval_Deref(self, node: Node) -> str:
        # TODO: *ptr が指す先の型を返す。
        raise NotImplementedError("type_of_lval_Deref を実装してください")

    def _load_ty(self, ty_str: str) -> None:
        # TODO: char/int/pointer のサイズに応じて lb/lw/ld を emit する。
        raise NotImplementedError("_load_ty を実装してください")

    def _convert_to(self, ty_str: str) -> None:
        # 提供済み: a0を代入先・固定仮引数・戻り値の型へ変換する。
        # char以外はここでレジスタの値を変えない。
        if ty_str == 'char':
            self.emit('  slli a0, a0, 56')
            self.emit('  srai a0, a0, 56')

    def _store_ty(self, ty_str: str) -> None:
        # char は sb で格納した後、self._convert_to(ty_str)で式の値も縮小する。
        # 代入式の結果にも縮小後の値を残す（例: c = 300 の値は44）。
        # TODO: char/int/pointer のサイズに応じて sb/sw/sd を emit する。
        raise NotImplementedError("_store_ty を実装してください")

    # 一時値の退避・復元はコマ2の _push_a0 / _pop_into をそのまま継承して使う。
    # （ここで同名のメソッドを定義し直すと self._depth が更新されなくなり、
    #   コマ6の call 前アラインメント判定が黙って壊れる）

    def codegen_Var(self, node: Node) -> None:
        # TODO: 変数の型に応じたロードを使う。
        raise NotImplementedError("codegen_Var を実装してください")

    def codegen_Assign(self, node: Node) -> None:
        # TODO: 左辺値の型に応じたストアを使う。
        raise NotImplementedError("codegen_Assign を実装してください")

    def codegen_Deref(self, node: Node) -> None:
        # TODO: ポインタの指す型に応じたロードを使う。
        raise NotImplementedError("codegen_Deref を実装してください")

    # codegen() は上書きしない。コマ8で新しく増える式の種類は無く、
    # 型対応が必要な Var / Assign / Deref は上のメソッド上書きだけで差し替わるため、
    # ディスパッチはコマ7までのものをそのまま継承する。
    # （ここで全 case を並べ直すと、コマ4の Cond やコマ5の PreInc/PreDec が落ちる。
    #   _type_of_expr が Cond を扱えるのも、この継承したディスパッチが前提）

    def collect_decls_Decl(self, node: Node) -> None:
        # TODO: node.ty_str or 'int' を使って型付きで alloc_local する。
        raise NotImplementedError("collect_decls_Decl を実装してください")

    def collect_decls(self, node: Node) -> None:
        match node.kind:
            case 'Decl':
                self.collect_decls_Decl(node)
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

    def _gen_call(self, name: str, args: list[Node]) -> None:
        # char固定引数がなければ、自分のコマ6の処理をそのまま使える。
        if 'char' not in self._function_params.get(name, []):
            super()._gen_call(name, args)
            return
        # TODO: 自分のコマ6の呼出し処理を再利用する。
        # 各実引数の評価後・退避前に、固定部ならself._function_params[name][i]へ
        # self._convert_to()で変換する。可変長部は縮小しない。
        # _depthとcall直前の16バイト整列を引き継ぐ。
        raise NotImplementedError("_gen_call を型対応で実装してください")

    def gen_stmt_Return(self, node: Node) -> None:
        # int・ポインタ・return;は、自分のコマ4の処理をそのまま使える。
        if self._return_ty != 'char' or node.operand is None:
            super().gen_stmt_Return(node)
            return
        # TODO: operandがあれば評価し、self._return_tyへself._convert_to()で変換する。
        # 共通エピローグへ飛ぶ。return;は値を評価・変換しない。
        raise NotImplementedError("gen_stmt_Return を型対応で実装してください")

    def _alloc_params(self, node: Node) -> None:
        # TODO: パラメータを p.ty_str or 'int' で型付き alloc_local する。
        raise NotImplementedError("_alloc_params（型対応版）を実装してください")

    def _reset_func_state(self, node: Node) -> int:
        self._locals.clear()
        self._stack_offset = 0
        self._ret_label = self.new_label()
        self._break_stack.clear()
        self._continue_stack.clear()
        self._alloc_params(node)
        self.collect_decls(node.body)
        self._current_params = node.params
        self._return_ty = node.ty_str or 'int'
        return self.align_to(self._stack_offset, 16)

    def _emit_func_prologue(self, name: str, frame_size: int) -> None:
        self.emit(f'  .globl {name}')
        self.emit(f'{name}:')
        self.emit(f'  addi sp, sp, -{frame_size + 16}')
        self.emit(f'  sd ra, {frame_size + 8}(sp)')
        self.emit(f'  sd s0, {frame_size}(sp)')
        self.emit(f'  addi s0, sp, {frame_size + 16}')
        # TODO: パラメータ保存も型サイズを意識して実装する。
        raise NotImplementedError("パラメータのスタック退避（型対応版）を実装してください")


Codegen = Codegen08


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/08_types/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source, filename)
    tokens = tokenize(source, filename)
    prog = parse(tokens)
    cg = Codegen08()
    cg.collect_function_returns(prog)
    cg.emit('  .text')
    for node in prog:
        cg.gen_func(node)
    sys.stdout.write(cg.output())


if __name__ == '__main__':
    main()
