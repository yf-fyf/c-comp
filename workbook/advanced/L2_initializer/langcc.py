#!/usr/bin/env python3
"""langcc — 初期化子リストつきコンパイララッパー(完成済み。編集しない)

scaffold と mycc.py には手を入れず、次を差し込む。

  パーサ側:
    parse_expr    '{' で始まっていたら初期化子リストを読み、
                  kind='InitList'、args=[式...] の Node を返す
                  (宣言の '=' の右側は parse_expr が呼ばれるので、これだけで足りる)

  コード生成側:
    gen_stmt          'Decl' が配列の初期化なら initializer.py の実装に回す
    collect_globals   グローバルの初期化子ノードを保持する
    emit_data_section 配列の初期化を .data に展開する
    補助メソッド      array_len / elem_size / const_value / local_offset / store_insn

使い方:
    python3 langcc.py file.c
    python3 scaffold/test_runner.py --compiler advanced/L2_initializer/langcc.py

環境変数:
    LANGCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    LANGCC_PASSES    initializer.py のあるディレクトリ(既定: このファイルの場所)
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


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def find_codegen_class(mod):
    best = None
    for _, obj in vars(mod).items():
        if inspect.isclass(obj) and hasattr(obj, "gen_stmt") and hasattr(obj, "emit"):
            if best is None or issubclass(obj, best):
                best = obj
    if best is None:
        raise RuntimeError("コード生成クラスが見つからない")
    return best


def is_array_ty(ty):
    return ty.endswith(']')


def install_parser_shim(real_parser, ast_def):
    """parse_expr が '{' を初期化子リストとして読めるようにする。"""

    class InitParser(real_parser.Parser):
        def parse_expr(self):
            if self.cur.sval == '{':
                line = self.cur.line
                self.pos += 1
                items = []
                if self.cur.sval != '}':
                    items.append(self.parse_expr())
                    while self.consume_if(','):
                        if self.cur.sval == '}':
                            break          # 末尾のカンマを許す
                        items.append(self.parse_expr())
                self.expect('}')
                return ast_def.Node('InitList', args=items, line=line)
            return super().parse_expr()

    shim = types.ModuleType("parser")
    shim.Parser = InitParser
    shim.parse = lambda tokens: InitParser(tokens).parse_program()
    sys.modules["parser"] = shim


def patch(cls, mycc, ini):
    orig_gen_stmt = cls.gen_stmt
    orig_collect_globals = cls.collect_globals
    orig_emit_data = cls.emit_data_section

    # ---- initializer.py から使う補助メソッド ----

    def array_len(self, ty):
        """'int[3]' → 3。配列でなければ None。"""
        if not is_array_ty(ty):
            return None
        return int(ty[ty.rindex('[') + 1:-1])

    def elem_size(self, ty):
        """配列の要素1個のサイズ。配列でなければその型のサイズ。"""
        base = ty[:ty.rindex('[')] if is_array_ty(ty) else ty
        return mycc.size_of_ty_str(base, self._struct_defs)

    def const_value(self, node):
        """定数式ノードの値。取れなければ 0。"""
        v = self._const_int_value(node)
        if v is None and node.kind == 'Num':
            v = node.val
        return 0 if v is None else v

    def local_offset(self, name):
        """ローカル変数の s0 からのオフセット。"""
        return self._locals[name][0]

    def store_insn(self, size):
        return {1: 'sb', 4: 'sw', 8: 'sd'}.get(size, 'sd')

    # ---- 差し込み ----

    def gen_stmt(self, node):
        if (node.kind == 'Decl' and node.init_expr is not None
                and is_array_ty(node.ty_str or '')):
            return ini.gen_local_init(self, node)
        return orig_gen_stmt(self, node)

    def collect_globals(self, prog):
        orig_collect_globals(self, prog)
        self._g_init_nodes = {}
        for n in prog:
            if n.kind == 'Decl' and n.init_expr is not None \
                    and is_array_ty(n.ty_str or ''):
                self._g_init_nodes[n.name] = n.init_expr
                # .bss ではなく .data 側へ出すため、初期化済みとして印を付ける
                ty, _ = self._globals[n.name]
                self._globals[n.name] = (ty, 0)

    def emit_data_section(self):
        arrays = getattr(self, '_g_init_nodes', {})
        if not arrays:
            return orig_emit_data(self)
        # 配列以外は元の処理に任せ、配列だけ自分で出す
        saved = {}
        for name in arrays:
            saved[name] = self._globals.pop(name)
        buf = []
        real_emit = self.emit
        self.emit = lambda line: buf.append(line)
        try:
            orig_emit_data(self)
        finally:
            self.emit = real_emit
        self._globals.update(saved)

        if not buf:
            real_emit('  .data')
        for line in buf:
            real_emit(line)
        for name, init_node in arrays.items():
            ty, _ = self._globals[name]
            real_emit(f'  .globl {name}')
            real_emit(f'{name}:')
            for line in ini.global_init_data(self, ty, init_node):
                real_emit(line)

    cls.array_len = array_len
    cls.elem_size = elem_size
    cls.const_value = const_value
    cls.local_offset = local_offset
    cls.store_insn = store_insn
    cls.gen_stmt = gen_stmt
    cls.collect_globals = collect_globals
    cls.emit_data_section = emit_data_section


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
    import parser as real_parser
    import ast_def

    install_parser_shim(real_parser, ast_def)
    ini = load_module("langcc_initializer", passes_dir / "initializer.py")
    mycc = load_module("mycc_under_langcc", compiler)
    patch(find_codegen_class(mycc), mycc, ini)

    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    with redirect_stdout(buf):
        mycc.main()
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
