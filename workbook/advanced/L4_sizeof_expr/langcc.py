#!/usr/bin/env python3
"""langcc — sizeof 単項式つきコンパイララッパー(完成済み。編集しない)

scaffold と mycc.py には手を入れず、次を差し込む。

  字句側:
    変更なし。'sizeof' は標準トラックでもキーワードとして読めている。

  構文側:
    _parse_sizeof  'sizeof' の次を1トークンだけ先読みして形式を決める
                   '(' + 型キーワード → 従来どおり SizeofType(ty_str=…)
                   それ以外           → SizeofExpr(operand=unary_expr)
                   sizeof が結合するのは unary_expr なので、
                   sizeof x + 1 は (sizeof x) + 1 と読まれる

  コード生成側:
    codegen        'SizeofExpr' を sizeofexpr.py の実装に回す。
                   回し方は次の3段で、オペランドの codegen は一度も呼ばない
                   (呼んだ時点で「評価しない」という意味論が壊れる)。
                       ty = static_type_of(cg, node.operand)
                       reject_incomplete(cg, ty, node.line)
                       gen_sizeof_expr(cg, ty)
    _type_of_expr  sizeof 式の型は int
    補助メソッド   type_size / is_ptr / elem_ty / lval_type /
                   var_type / struct_tags

  文字列リテラルの収集について:
    collect_strings_expr は知らない kind を素通りする。sizeof のオペランドは
    評価されないので、sizeof "abc" のラベルを作らないこの挙動でちょうどよい。
    (sizeof "abc" は char* のサイズ = 8 であって中身は要らない)

使い方:
    python3 langcc.py file.c
    python3 scaffold/test_runner.py --compiler advanced/L4_sizeof_expr/langcc.py

環境変数:
    LANGCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    LANGCC_PASSES    sizeofexpr.py のあるディレクトリ(既定: このファイルの場所)
"""

import importlib.util
import inspect
import io
import os
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"

# sizeof 式のノード種別(langcc と sizeofexpr.py で共有する)
ND_SIZEOF_EXPR = 'SizeofExpr'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def find_codegen_class(mod):
    best = None
    for _, obj in vars(mod).items():
        if inspect.isclass(obj) and hasattr(obj, "codegen") and hasattr(obj, "emit"):
            if best is None or issubclass(obj, best):
                best = obj
    if best is None:
        raise RuntimeError("コード生成クラスが見つからない")
    return best


def install_parser_shim(real_parser, ast_def):
    """_parse_sizeof が式形式も読めるようにする。

    scaffold の _parse_sizeof は「'(' のあとが型キーワードでなければ構文エラー」
    としている。ここを「型名形式でなければ式形式」に置き換えるだけでよい。
    """

    class SizeofExprParser(real_parser.Parser):
        def _parse_sizeof(self):
            line = self.cur.line
            self.pos += 1                       # 'sizeof'
            if self.cur.sval == '(' and self._peek_is_type():
                self.expect('(')
                ty = self.parse_obj_type()
                self.expect(')')
                return ast_def.Node('SizeofType', ty_str=ty, line=line)
            # 式形式。オペランドは unary_expr(sizeof は単項演算子)
            return ast_def.Node(ND_SIZEOF_EXPR,
                                operand=self._parse_unary(), line=line)

    shim = types.ModuleType("parser")
    shim.Parser = SizeofExprParser
    shim.parse = lambda tokens: SizeofExprParser(tokens).parse_program()
    sys.modules["parser"] = shim
    return shim


def patch(cls, mycc, comp):
    orig_codegen = cls.codegen
    orig_type_of_expr = cls._type_of_expr

    # ---- sizeofexpr.py から使う補助メソッド ----

    def type_size(self, ty):
        """型文字列のバイト数('int'→4、'char'→1、ポインタ→8、struct→定義から)。"""
        return mycc.size_of_ty_str(ty, self._struct_defs)

    def is_ptr(self, ty):
        """ポインタ型なら True。"""
        return mycc.is_ptr_ty_str(ty)

    def elem_ty(self, ty):
        """ポインタ型の指す先の型('int*'→'int')。ポインタでなければそのまま。"""
        return mycc.elem_ty_str(ty)

    def lval_type(self, node):
        """左辺値ノード(Var / Deref / Index / Member)の型文字列。"""
        return self._type_of_lval(node)

    def var_type(self, name, line):
        """変数名から型文字列を引く(局所 → 大域の順)。"""
        return self.lookup_var_ty(name, line)

    def struct_tags(self):
        """本体まで定義されている構造体型の名前('struct Point' など)。

        前方宣言だけの構造体(lib.h の struct FILE など)はここに現れない。
        """
        return tuple(self._struct_defs)

    # ---- 差し込み ----

    def codegen(self, node):
        if node is not None and node.kind == ND_SIZEOF_EXPR:
            ty = comp.static_type_of(self, node.operand)
            comp.reject_incomplete(self, ty, node.line)
            return comp.gen_sizeof_expr(self, ty)
        return orig_codegen(self, node)

    def _type_of_expr(self, node):
        if node is not None and node.kind == ND_SIZEOF_EXPR:
            return 'int'
        return orig_type_of_expr(self, node)

    cls.type_size = type_size
    cls.is_ptr = is_ptr
    cls.elem_ty = elem_ty
    cls.lval_type = lval_type
    cls.var_type = var_type
    cls.struct_tags = struct_tags
    cls.codegen = codegen
    cls._type_of_expr = _type_of_expr


def main():
    srcs = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not srcs:
        print("使い方: python3 langcc.py file.c ...", file=sys.stderr)
        raise SystemExit(2)

    passes_dir = Path(os.environ.get("LANGCC_PASSES", DIR))
    compiler = Path(os.environ.get("LANGCC_COMPILER", WORKBOOK / "final" / "mycc.py"))
    if not compiler.is_file():
        print(f"ベースのコンパイラが見つからない: {compiler}", file=sys.stderr)
        raise SystemExit(2)

    sys.path.insert(0, str(SCAFFOLD))
    comp = load_module("langcc_sizeofexpr", passes_dir / "sizeofexpr.py")

    import parser as real_parser
    import ast_def

    install_parser_shim(real_parser, ast_def)
    mycc = load_module("mycc_under_langcc", compiler)
    patch(find_codegen_class(mycc), mycc, comp)

    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    with redirect_stdout(buf):
        mycc.main()
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
