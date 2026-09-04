#!/usr/bin/env python3
"""langcc — 構造体の値渡し・値返しつきコンパイララッパー(完成済み。編集しない)

scaffold と mycc.py には手を入れず、次を差し込む。

  字句側:
    変更なし。

  構文側:
    parse_program  戻り値型を ret_type ::= scalar_type | 'void' | 'struct' IDENT へ拡張する
                   (本家は「struct 値の戻り値は使えません」で弾く)
                   struct 値を返す関数の名前と型は STRUCT_RET_FUNCS に覚えておく
    _parse_func    仮引数を param ::= obj_type IDENT へ拡張する
                   (本家は parse_scalar_type なので struct 値の仮引数を弾く)

  コード生成側:
    _type_of_expr / _type_of_lval
                   'Call' の型を STRUCT_RET_FUNCS から引く(本家は常に 'int')
    codegen        'Assign' が構造体どうしなら byval.copy_struct でまるごと写す
                   (S3 で実装済みの機能。この回では前提として完成品を配る。
                    ただし右辺は codegen で評価するので `q = make(1, 2);` も書ける)
                   'Call' が struct 値を返すなら byval.gen_sret_call に回す
    codegen_lval   struct 値を返す 'Call' もアドレスを持つ式として扱う
                   (これで `f(make(1, 2))` や `make(1, 2).x` が書ける)
    _gen_call      各実引数の生成を byval.gen_arg に回す
    collect_decls  フレームに隠しスロットを先に確保する
                     .sretp  … 自分が struct 値を返すとき、呼び出し側から渡される
                               隠しポインタの置き場(8バイト)
                     .sretN  … 自分が struct 値を返す関数を呼ぶとき、
                               戻り値を受け取る一時領域(呼び出し1箇所につき1個)
    gen_stmt       本体の先頭で byval.gen_param_prologue を呼ぶ
                   'Return' で struct 値を返すときは byval.gen_struct_return に回す

  この教材の呼び出し規約(gcc の RV64 ABI とは非互換。資料に明記してある):
    - struct 値の実引数は「アドレスを 1 個の引数スロットで渡す」。
      コピーするのは呼ばれ側だけ(単一コピー)。
    - struct 値の戻り値は「呼び出し側が用意した領域へのポインタ」を
      **末尾の追加引数**として渡す(実 ABI は a0 = 先頭に置く)。
      よって struct 値を返す関数のユーザ引数は 7 個までになる。

使い方:
    python3 langcc.py file.c
    python3 scaffold/test_runner.py --compiler advanced/L5_struct_byval/langcc.py

環境変数:
    LANGCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    LANGCC_PASSES    byval.py のあるディレクトリ(既定: このファイルの場所)
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

# 引数レジスタは a0〜a7 の 8 本。隠しポインタもこの 8 本を 1 本使う
MAX_ARGS = 8

# 関数名 → 戻り値の構造体型('struct Point' など)。parser shim が埋める
STRUCT_RET_FUNCS = {}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def find_codegen_class(mod):
    best = None
    for _, obj in vars(mod).items():
        if inspect.isclass(obj) and hasattr(obj, "gen_func") and hasattr(obj, "emit"):
            if best is None or issubclass(obj, best):
                best = obj
    if best is None:
        raise RuntimeError("コード生成クラスが見つからない")
    return best


def install_parser_shim(real_parser):
    """param と ret_type を拡張した Parser を sys.modules["parser"] に入れる。

    scaffold/parser.py の Parser を継承した複製クラスを作り、
    parse_program と _parse_func だけを差し替える(scaffold には触らない)。
    このあとに読み込む mycc も `from parser import parse` でこの複製を掴む。
    """
    Node = real_parser.Node
    parse_error = real_parser._parse_error

    class ByvalParser(real_parser.Parser):
        def parse_program(self):
            nodes = []
            if self.cur.kind == real_parser.TK_EOF:
                parse_error("プログラムには 1 個以上の外部宣言が必要です")
            while self.cur.kind != real_parser.TK_EOF:
                # struct 定義・前方宣言(AST には出さない)
                if self.cur.sval == 'struct' and self.peek(2).sval in ('{', ';'):
                    self._parse_struct_decl()
                    continue

                line = self.cur.line
                base, stars = self._parse_base_and_stars()
                name = self.expect_ident()

                if self.cur.sval == '(':
                    # ret_type ::= scalar_type | 'void' | 'struct' IDENT
                    # 本家はここで struct 値の戻り値を弾く。この回の拡張は通す
                    if base.startswith('struct') and not stars:
                        STRUCT_RET_FUNCS[name] = base
                    nodes.append(self._parse_func(base + stars, name))
                else:
                    if base == 'void' and not stars:
                        parse_error("void 型の変数は宣言できません", line)
                    self.expect(';')
                    nodes.append(Node(real_parser.ND_DECL,
                                      name=name, ty_str=base + stars))
            # struct 定義自体は self.struct_defs へ積まれている
            # (_parse_struct_decl は scaffold/parser.py の実装をそのまま継承する)。
            # ここで Program として包まないと、mycc 側の parse_struct_defs(prog) が
            # getattr(prog, 'struct_defs', []) で空を返してしまう。
            return real_parser.Program(nodes, self.struct_defs)

        def _parse_func(self, ty_str, name):
            self.expect('(')
            params = []
            variadic = False

            if not self.consume_if(')'):
                while True:
                    if self.cur.sval == '...':
                        if not params:
                            parse_error(
                                "可変長 '...' は 1 個以上の固定引数の後にのみ書けます",
                                self.cur.line)
                        self.pos += 1
                        variadic = True
                        break
                    # param ::= obj_type IDENT
                    # 本家は parse_scalar_type なので struct 値の仮引数を弾く。
                    # obj_type にすると struct 値を書けるようになる(void は不可のまま)
                    p_ty = self.parse_obj_type()
                    p_name = self.expect_ident()   # 仮引数は名前必須
                    params.append(Node(real_parser.ND_DECL,
                                       name=p_name, ty_str=p_ty))
                    if not self.consume_if(','):
                        break
                self.expect(')')

            if self.consume_if(';'):
                return Node(real_parser.ND_FUNCPROTO,
                            name=name, ty_str=ty_str, params=params)

            if variadic:
                parse_error("可変長 '...' はプロトタイプ宣言でのみ使えます", self.cur.line)
            body = self.parse_func_body()
            return Node(real_parser.ND_FUNCDEF, name=name, ty_str=ty_str,
                        params=params, body=body)

    shim = types.ModuleType("parser")
    shim.Parser = ByvalParser
    shim.parse = lambda tokens: ByvalParser(tokens).parse_program()
    sys.modules["parser"] = shim
    return shim


def _walk_struct_ret_calls(node, out):
    """node 以下から「struct 値を返す関数の呼び出し」ノードを順に集める。"""
    if node is None:
        return
    if isinstance(node, list):
        for item in node:
            _walk_struct_ret_calls(item, out)
        return
    if not hasattr(node, 'kind'):
        return
    for name in ('lhs', 'rhs', 'cond', 'then', 'else_',
                 'init', 'step', 'body', 'operand'):
        _walk_struct_ret_calls(getattr(node, name, None), out)
    for name in ('stmts', 'args'):
        _walk_struct_ret_calls(getattr(node, name, None), out)
    if node.kind == 'Call' and node.name in STRUCT_RET_FUNCS:
        out.append(node)


def patch(cls, mycc, bv):
    orig_codegen = cls.codegen
    orig_codegen_lval = cls.codegen_lval
    orig_type_of_expr = cls._type_of_expr
    orig_type_of_lval = cls._type_of_lval
    orig_gen_func = cls.gen_func
    orig_gen_stmt = cls.gen_stmt
    orig_collect_decls = cls.collect_decls

    # ---- byval.py から使う補助メソッド ----

    def struct_size(self, ty):
        """構造体型ならバイト数、そうでなければ None。"""
        if ty and mycc.is_struct_ty_str(ty, self._struct_defs):
            return mycc.size_of_ty_str(ty, self._struct_defs)
        return None

    def expr_type(self, node):
        """式ノードの型(文字列)。struct 値を返す呼び出しは構造体型になる。"""
        return self._type_of_expr(node)

    def frame_offset(self, name):
        """局所変数(仮引数を含む)の s0 からのオフセット。"""
        return self._locals[name][0]

    def current_params(self):
        """いま生成中の関数の仮引数を [(引数レジスタ番号, 名前, 型), ...] で返す。"""
        return list(self._bv_params)

    def current_ret_type(self):
        """いま生成中の関数の戻り値型(文字列)。"""
        return self._bv_ret_ty

    def sret_param(self):
        """struct 値を返す関数なら (隠しポインタの引数レジスタ番号, 置き場のオフセット)。

        struct 値を返さない関数では None。
        """
        if self._bv_ret_size is None:
            return None
        return (len(self._bv_params), self._locals['.sretp'][0])

    def sret_slot_addr(self, node):
        """呼び出しノード node の戻り値受け取り領域のアドレスを a0 に置く。"""
        name = self._bv_sret_slots[id(node)]
        self.emit(f'  addi a0, s0, {self._locals[name][0]}')

    def emit_call(self, name, nargs):
        """スタックに積んだ nargs 個の引数を a0〜 に配し、name を呼ぶ(完成済み)。

        mycc の _gen_call の後半と同じ手順。sp の 16 バイトアラインメントもここで面倒を見る。
        """
        if nargs > MAX_ARGS:
            raise RuntimeError(
                f"引数が多すぎます({nargs} 個 > {MAX_ARGS} 個): '{name}' — "
                "struct 値を返す関数は隠しポインタで 1 個使うので、ユーザ引数は 7 個まで")
        for i in range(nargs):
            self.emit(f'  ld a{i}, {(nargs - 1 - i) * 8}(sp)')
        if nargs:
            self.emit(f'  addi sp, sp, {nargs * 8}')
            self._depth -= nargs
        pad = 8 if self._depth % 2 else 0
        if pad:
            self.emit(f'  addi sp, sp, -{pad}')
        self.emit(f'  call {name}')
        if pad:
            self.emit(f'  addi sp, sp, {pad}')

    # ---- 型 ----

    def _type_of_expr(self, node):
        if node is not None and node.kind == 'Call' and node.name in STRUCT_RET_FUNCS:
            return STRUCT_RET_FUNCS[node.name]
        return orig_type_of_expr(self, node)

    def _type_of_lval(self, node):
        if node is not None and node.kind == 'Call' and node.name in STRUCT_RET_FUNCS:
            return STRUCT_RET_FUNCS[node.name]
        return orig_type_of_lval(self, node)

    # ---- 式 ----

    def _is_struct_assign(self, node):
        return (node.kind == 'Assign'
                and self.struct_size(self._type_of_lval(node.lhs)) is not None)

    def codegen(self, node):
        if node is not None:
            if node.kind == 'Call' and node.name in STRUCT_RET_FUNCS:
                return bv.gen_sret_call(self, node)
            if _is_struct_assign(self, node):
                # S3 で実装した構造体代入。この回では完成品として配る。
                # 右辺は codegen で評価するので、struct 値を返す呼び出しも書ける
                size = self.struct_size(self._type_of_lval(node.lhs))
                self.codegen_lval(node.lhs)
                self._push_a0()
                self.codegen(node.rhs)
                self._pop_into('a1')
                bv.copy_struct(self, size)
                self.emit('  mv a0, a1')
                return None
        return orig_codegen(self, node)

    def codegen_lval(self, node):
        if node is not None and node.kind == 'Call' and node.name in STRUCT_RET_FUNCS:
            # 戻り値は呼び出し側フレームの一時領域にある。そこがアドレス
            return bv.gen_sret_call(self, node)
        return orig_codegen_lval(self, node)

    def _gen_call(self, name, args):
        for arg in args:
            bv.gen_arg(self, arg)
            self._push_a0()
        self.emit_call(name, len(args))

    # ---- 関数 ----

    def gen_func(self, node):
        if node.kind != 'FuncDef':
            return orig_gen_func(self, node)
        self._bv_params = [(i, p.name, p.ty_str or 'int')
                           for i, p in enumerate(node.params)]
        self._bv_ret_ty = node.ty_str or 'int'
        self._bv_ret_size = (mycc.size_of_ty_str(self._bv_ret_ty, self._struct_defs)
                             if node.name in STRUCT_RET_FUNCS else None)
        self._bv_sret_calls = []
        _walk_struct_ret_calls(node.body, self._bv_sret_calls)
        self._bv_sret_slots = {}
        self._bv_reserve = True
        self._bv_need_prologue = (
            self._bv_ret_size is not None
            or any(self.struct_size(ty) is not None for _, _, ty in self._bv_params))
        return orig_gen_func(self, node)

    def collect_decls(self, node):
        # gen_func から最初に呼ばれるタイミングで隠しスロットを確保する
        if getattr(self, '_bv_reserve', False):
            self._bv_reserve = False
            if self._bv_ret_size is not None:
                self.alloc_local('.sretp', 'void*')
            for k, call in enumerate(self._bv_sret_calls):
                slot = f'.sret{k}'
                self.alloc_local(slot, STRUCT_RET_FUNCS[call.name])
                self._bv_sret_slots[id(call)] = slot
        return orig_collect_decls(self, node)

    def gen_stmt(self, node):
        if getattr(self, '_bv_need_prologue', False):
            self._bv_need_prologue = False
            bv.gen_param_prologue(self)
        if (node is not None and node.kind == 'Return'
                and node.operand is not None and self._bv_ret_size is not None):
            bv.gen_struct_return(self, node)
            self.emit(f'  j {self._ret_label}')
            return None
        return orig_gen_stmt(self, node)

    cls.struct_size = struct_size
    cls.expr_type = expr_type
    cls.frame_offset = frame_offset
    cls.current_params = current_params
    cls.current_ret_type = current_ret_type
    cls.sret_param = sret_param
    cls.sret_slot_addr = sret_slot_addr
    cls.emit_call = emit_call
    cls._type_of_expr = _type_of_expr
    cls._type_of_lval = _type_of_lval
    cls.codegen = codegen
    cls.codegen_lval = codegen_lval
    cls._gen_call = _gen_call
    cls.gen_func = gen_func
    cls.collect_decls = collect_decls
    cls.gen_stmt = gen_stmt


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

    install_parser_shim(real_parser)
    bv = load_module("langcc_byval", passes_dir / "byval.py")
    mycc = load_module("mycc_under_langcc", compiler)
    patch(find_codegen_class(mycc), mycc, bv)

    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    with redirect_stdout(buf):
        mycc.main()
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
