#!/usr/bin/env python3
"""langcc — 複合代入つきコンパイララッパー(完成済み。編集しない)

scaffold と mycc.py には手を入れず、次を差し込む。

  字句側:
    lexer モジュールの複製を sys.modules["lexer"] に注入し、その
    TWO_CHAR_PUNCTS を compound.py の extend_puncts() で拡張する
    (標準トラックの字句には '+=' '-=' '*=' '/=' '%=' が無い)

  構文側:
    _parse_assign  cond まで読んだあと複合代入演算子なら
                   kind='CompoundAssign'、sval=演算子、lhs / rhs の Node を返す
                   (右結合。x = x + e への脱糖はしない — 左辺を2回評価するため)

  コード生成側:
    codegen              'CompoundAssign' を compound.py の実装に回す
    _type_of_expr        複合代入式の型は左辺の型
    collect_strings_expr 右辺の文字列リテラルも拾えるようにする
    補助メソッド         push_a0 / pop_into / load_ty / store_ty /
                         lval_type / ptr_elem_size

使い方:
    python3 langcc.py file.c
    python3 scaffold/test_runner.py --compiler advanced/L2_compound_assign/langcc.py

環境変数:
    LANGCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    LANGCC_PASSES    compound.py のあるディレクトリ(既定: このファイルの場所)
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

# 複合代入演算子(langcc と compound.py で共有する)
COMPOUND_OPS = ('+=', '-=', '*=', '/=', '%=')


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


def install_lexer_shim(comp):
    """複合代入トークンを読める lexer を sys.modules["lexer"] に入れる。

    scaffold/lexer.py をもう1つ別のモジュールとして読み込み、その複製の
    TWO_CHAR_PUNCTS だけを差し替える(tokenize はモジュール変数を見るので、
    複製側だけが拡張され、scaffold 本体の字句解析器は無傷のまま)。
    このあとに読み込む parser も mycc も `from lexer import ...` で
    この複製を掴む。
    """
    shim = load_module("lexer", SCAFFOLD / "lexer.py")
    shim.TWO_CHAR_PUNCTS = comp.extend_puncts(list(shim.TWO_CHAR_PUNCTS))
    return shim


def install_parser_shim(real_parser, ast_def):
    """_parse_assign が複合代入を読めるようにする。"""

    class CompoundParser(real_parser.Parser):
        def _parse_assign(self):
            node = self._parse_cond()
            op = self.cur.sval
            if op in COMPOUND_OPS:
                line = self.cur.line
                self.pos += 1
                rhs = self._parse_assign()          # 右結合
                return ast_def.Node('CompoundAssign', sval=op,
                                    lhs=node, rhs=rhs, line=line)
            if self.consume_if('='):
                return ast_def.Node('Assign', lhs=node,
                                    rhs=self._parse_assign(), line=node.line)
            return node

    shim = types.ModuleType("parser")
    shim.Parser = CompoundParser
    shim.parse = lambda tokens: CompoundParser(tokens).parse_program()
    sys.modules["parser"] = shim
    return shim


def patch(cls, mycc, comp):
    orig_codegen = cls.codegen
    orig_type_of_expr = cls._type_of_expr
    orig_collect_strings_expr = cls.collect_strings_expr

    # ---- compound.py から使う補助メソッド ----

    def push_a0(self):
        """a0 の値をスタックに積む。"""
        self._push_a0()

    def pop_into(self, reg):
        """スタックの一番上を reg に取り出す。"""
        self._pop_into(reg)

    def load_ty(self, ty):
        """a0 が指すアドレスから ty の値を読んで a0 に入れる(lb/lw/ld)。"""
        self._load_ty(ty)

    def store_ty(self, ty):
        """a1 が指すアドレスへ a0 の値を書く(sb/sw/sd)。"""
        self._store_ty(ty)

    def lval_type(self, node):
        """左辺値ノードの型文字列('int'、'char'、'int*' など)。"""
        return self._type_of_lval(node)

    def ptr_elem_size(self, ty):
        """ポインタ型なら要素1個のバイト数、ポインタでなければ 0。"""
        if not mycc.is_ptr_ty_str(ty):
            return 0
        return mycc.size_of_ty_str(mycc.elem_ty_str(ty), self._struct_defs)

    # ---- 差し込み ----

    def codegen(self, node):
        if node is not None and node.kind == 'CompoundAssign':
            return comp.gen_compound_assign(self, node)
        return orig_codegen(self, node)

    def _type_of_expr(self, node):
        if node is not None and node.kind == 'CompoundAssign':
            return self._type_of_lval(node.lhs)
        return orig_type_of_expr(self, node)

    def collect_strings_expr(self, node):
        if node is not None and node.kind == 'CompoundAssign':
            self.collect_strings_expr(node.lhs)
            self.collect_strings_expr(node.rhs)
            return None
        return orig_collect_strings_expr(self, node)

    cls.push_a0 = push_a0
    cls.pop_into = pop_into
    cls.load_ty = load_ty
    cls.store_ty = store_ty
    cls.lval_type = lval_type
    cls.ptr_elem_size = ptr_elem_size
    cls.codegen = codegen
    cls._type_of_expr = _type_of_expr
    cls.collect_strings_expr = collect_strings_expr


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
    comp = load_module("langcc_compound", passes_dir / "compound.py")

    install_lexer_shim(comp)        # parser を読み込む前に字句を差し替える
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
