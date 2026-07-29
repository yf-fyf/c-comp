#!/usr/bin/env python3
"""O4: レジスタ割り当て(スケルトン)

局所変数をメモリではなく callee-saved レジスタ(s1〜s11)に置く。

これまでの回と違い、**アセンブリになる前のコード生成器**に手を入れる。
「どの変数の & が取られているか」は AST を見ないと分からないので、
アセンブリになってからでは遅い。

実装する順番:
    コマ1  Step 1: escaped_vars
           Step 2: promotable
           Step 3: emit_var_read / emit_var_assign
           Step 4: save_restore
           Step 6: worth_promoting は `return list(names)` にしておく
    コマ2  Step 5: assign_counts / has_call
           Step 6: worth_promoting を本実装にする

確認:
    python3 check.py
    python3 golden.py
"""

# 割り当てに使う callee-saved レジスタ。s0 はフレームポインタなので使わない。
SREGS = ['s1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9', 's10', 's11']


def walk(node, fn):
    """AST を辿って、ノードごとに fn を呼ぶ(完成済み)。"""
    if hasattr(node, 'kind'):
        fn(node)
        for value in vars(node).values():
            walk(value, fn)
    elif isinstance(node, (list, tuple)):
        for value in node:
            walk(value, fn)


# ---------------------------------------------------------------
# Step 1: 昇格できない変数を見つける
# ---------------------------------------------------------------


def escaped_vars(func_node):
    """`&x` の形でアドレスを取られている変数の名前の集合。

    アドレスを取るということは「メモリ上に実体が要る」ということなので、
    レジスタに置けない。
    """
    # TODO(Step 1)
    #
    # escaped = set() を用意し、walk(func_node.body, visit) で AST を歩く。
    # visit(n) の中で
    #   n.kind == 'Addr' かつ その operand が Var なら operand.name を集める。
    #
    # operand が Var とは限らない(`&a[i]` など)ので、
    # getattr(n, 'operand', None) と getattr(operand, 'kind', None) で確かめる。
    raise NotImplementedError("Step 1: escaped_vars を実装する")


# ---------------------------------------------------------------
# Step 2: 昇格する変数を選ぶ
# ---------------------------------------------------------------


def promotable(locals_, escaped):
    """レジスタに置ける変数の名前のリスト。

    locals_ は {変数名: (オフセット, 型文字列)} という辞書
    (コード生成器の `self._locals` がこの形をしている)。
    """
    # TODO(Step 2)
    #
    # 次を全部満たすものだけ残す。宣言された順に返す。
    #   - escaped に入っていない(アドレスを取られていない)
    #   - 型文字列に '[' を含まない(配列はレジスタに入らない)
    #   - 型が 'int' か、ポインタ(型文字列が '*' で終わる)
    #
    # struct はどちらの条件にも当てはまらないので自然に外れる。
    raise NotImplementedError("Step 2: promotable を実装する")


def assign(names):
    """変数名 → レジスタ名。レジスタが足りなければ余りはメモリのまま(完成済み)。"""
    return {name: SREGS[i] for i, name in enumerate(names) if i < len(SREGS)}


# ---------------------------------------------------------------
# Step 3: 変数の読み書きを出す
# ---------------------------------------------------------------


def emit_var_read(cg, reg):
    """昇格した変数を読む。`cg.emit(...)` で1行出す。"""
    # TODO(Step 3)
    #
    # メモリから読む代わりに、レジスタから a0 へ写すだけでよい。
    #     mv a0, <reg>
    raise NotImplementedError("Step 3: emit_var_read を実装する")


def emit_var_assign(cg, node, reg):
    """昇格した変数へ代入する。node は Assign ノード、reg は左辺のレジスタ。"""
    # TODO(Step 3)
    #
    #  1. 右辺を生成する。**cg.codegen(node.rhs)** を使うこと。
    #     元の codegen を直接呼ぶと右辺の部分木にパッチが効かず、
    #     `found = i;` のような代入で i が古いメモリから読まれてしまう。
    #  2. a0 の値をレジスタへ書く。
    #         <store_op(型)> <reg>, a0
    #     型は cg._locals[node.lhs.name][1] で引ける。
    #  3. a0 はそのままにする。a0 に残った右辺の値が代入式の値になる
    #     (元の生成と同じ意味)。
    #
    # アドレス計算も push/pop も store も要らなくなるのがこの回の効果である。
    raise NotImplementedError("Step 3: emit_var_assign を実装する")


def store_op(ty):
    """レジスタへ書き込むときの命令(完成済み)。

    `int` はメモリでは sw/lw で32ビットに切り詰められていた。
    レジスタに置くとその切り詰めが起きなくなるので、sext.w で明示的に行う
    (S2「int は64ビットで計算されている」と直結する)。
    """
    return 'mv' if ty.endswith('*') else 'sext.w'


# ---------------------------------------------------------------
# Step 4: 退避と復帰
# ---------------------------------------------------------------


def save_restore(cg, used, op):
    """使う callee-saved レジスタを退避(`op='sd'`)または復帰(`op='ld'`)する。"""
    # TODO(Step 4)
    #
    # used の各レジスタ r について1行ずつ出す。
    #     <op> <r>, <退避スロットのオフセット>(s0)
    # 退避スロットは gen_func が `__save_<r>` という名前で確保してあるので、
    #     cg._locals["__save_" + r][0]
    # でオフセットが引ける。
    #
    # これを忘れると、呼び出し元が使っていた s レジスタを壊す。
    # fixed15 は通ってしまうことがあるので、**静かに壊れる**種類のバグになる。
    raise NotImplementedError("Step 4: save_restore を実装する")


# ---------------------------------------------------------------
# Step 5: 割に合うかを見る材料(コマ2)
# ---------------------------------------------------------------


def assign_counts(func_node):
    """変数ごとの代入回数(`x = 式` の左辺に現れた回数)。"""
    # TODO(Step 5)
    #
    # escaped_vars と同じく walk を使う。
    # n.kind == 'Assign' かつ n.lhs が Var のとき n.lhs.name の回数を増やす。
    # 返り値は {変数名: 回数}。
    raise NotImplementedError("Step 5: assign_counts を実装する")


def has_call(func_node):
    """関数の中に呼び出しがあるか(葉関数なら退避が要らない)。"""
    # TODO(Step 5)
    #
    # walk で n.kind == 'Call' が1つでもあれば True。
    raise NotImplementedError("Step 5: has_call を実装する")


# ---------------------------------------------------------------
# Step 6: 費用対効果で選ぶ
# ---------------------------------------------------------------


def worth_promoting(names, counts, calls):
    """割に合う変数だけを残す。

    利得は「代入が安くなること」で稼ぐ。
        x = 式  … アドレス計算 + push + pop + store の5命令 → 1命令
    読み出しは `lw` も `mv` も1命令なので、それだけでは得しない
    (O6 のコピー伝播まで進むと読み出しも得になる)。

    費用は callee-saved レジスタの退避・復帰で、呼び出しのたびにかかる。
    """
    # TODO(Step 6)
    #
    # **コマ1 では `return list(names)`(全部昇格)にしておく。**
    # その状態で golden.py を走らせると、fib_rec だけ遅くなることが分かる。
    #
    # コマ2 でここを本実装にする。
    #   - calls が偽(葉関数)なら退避が要らないので names をそのまま返す
    #   - calls が真なら counts.get(name, 0) > 0 の変数だけ残す
    #     (一度も代入されない変数は、昇格しても得をしないため)
    raise NotImplementedError("Step 6: worth_promoting を実装する")


# ---------------------------------------------------------------
# 組み立て(完成済み)
# ---------------------------------------------------------------


def decide_promotions(locals_, func_node):
    """この関数でレジスタに置く変数を決める。{変数名: レジスタ名} を返す。"""
    names = promotable(locals_, escaped_vars(func_node))
    names = worth_promoting(names, assign_counts(func_node), has_call(func_node))
    order = list(locals_)
    return assign(sorted(names, key=order.index))


def patch(cls, mycc=None):
    """コード生成クラスに、レジスタ割り当てを差し込む(完成済み)。

    `optcc.py --regalloc` がこの関数を呼ぶ。
    `codegen` と `gen_func` を差し替え、上で実装した関数を呼ぶ。
    """
    orig_codegen = cls.codegen

    def codegen(self, node):
        prom = getattr(self, '_prom', {})
        if node.kind == 'Var' and node.name in prom:
            emit_var_read(self, prom[node.name])
            return
        if node.kind == 'Assign' and getattr(node.lhs, 'kind', None) == 'Var' \
                and node.lhs.name in prom:
            emit_var_assign(self, node, prom[node.lhs.name])
            return
        orig_codegen(self, node)

    def gen_func(self, node):
        if node.kind != 'FuncDef':
            return
        self._locals.clear()
        self._stack_offset = 0
        self._ret_label = self.new_label()
        self._break_stack.clear()
        self._cont_stack.clear()
        for p in node.params:
            if p.name:
                self.alloc_local(p.name, p.ty_str or 'int')
        self.collect_decls(node.body)

        self._prom = decide_promotions(self._locals, node)
        used = [r for r in SREGS if r in set(self._prom.values())]
        for r in used:
            self.alloc_local(f'__save_{r}', 'long')
        frame = self._align_to(self._stack_offset, 16)

        # --- プロローグ ---
        self.emit(f'  .globl {node.name}')
        self.emit(f'{node.name}:')
        self.emit(f'  addi sp, sp, -{frame + 16}')
        self.emit(f'  sd ra, {frame + 8}(sp)')
        self.emit(f'  sd s0, {frame}(sp)')
        self.emit(f'  addi s0, sp, {frame + 16}')
        save_restore(self, used, 'sd')
        for i, p in enumerate(node.params):
            if not (p.name and i < 8 and p.name in self._locals):
                continue
            if p.name in self._prom:
                # 引数もメモリではなくレジスタで受け取る
                self.emit(f'  {store_op(self._locals[p.name][1])} '
                          f'{self._prom[p.name]}, a{i}')
            else:
                self.emit(f'  sd a{i}, {self._locals[p.name][0]}(s0)')

        self.gen_stmt(node.body)

        # --- エピローグ ---
        self.emit(f'{self._ret_label}:')
        save_restore(self, used, 'ld')
        self.emit(f'  ld s0, {frame}(sp)')
        self.emit(f'  ld ra, {frame + 8}(sp)')
        self.emit(f'  addi sp, sp, {frame + 16}')
        self.emit('  ret')

    cls.codegen = codegen
    cls.gen_func = gen_func
