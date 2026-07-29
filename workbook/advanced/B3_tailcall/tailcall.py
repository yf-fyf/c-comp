#!/usr/bin/env python3
"""B3: 末尾呼び出し最適化(スケルトン)

`return f(...);` の形で自分自身を呼んでいるとき、
新しいフレームを積む代わりに「引数を詰め替えて関数の先頭へ戻る」ようにする。

引数の cg はコード生成器のインスタンスで、次を使う。
    cg.emit(行)          アセンブリを1行出力する
    cg.codegen(式ノード)  式を評価して結果を a0 に置く
    cg._push_a0() / cg._pop_into(reg)   値の退避・復元
    cg.tc_func_name      いま生成中の関数名
    cg.tc_params         いま生成中の関数の引数ノード一覧
    cg.tc_label          関数本体の先頭ラベル(ここへ j で戻る)

実装する順番:
    Step 1: is_self_tail_call
    Step 2: gen_tail_call

確認:
    python3 check.py
    python3 golden.py
"""


def param_offsets(cg):
    """いま生成中の関数の引数について [(名前, s0 からのオフセット)] を返す(完成済み)。"""
    out = []
    for p in cg.tc_params:
        if p.name and p.name in cg._locals:
            out.append((p.name, cg._locals[p.name][0]))
    return out


def is_self_tail_call(cg, node):
    """Step 1: node が「自分自身への末尾呼び出し」の return 文かどうか。

    方針(すべて満たすときだけ True):
    - node.kind が 'Return' で、node.operand がある
    - node.operand.kind が 'Call' で、name が cg.tc_func_name と同じ
    - 引数の個数が param_offsets(cg) の個数と一致し、8個以内

    注意: return f(x) + 1; は末尾呼び出しではない(呼び出しの後に足し算が残る)。
    この判定では node.operand が Call そのものであることを見ているので、
    その場合は自然に False になる。
    """
    raise NotImplementedError("Step 1: is_self_tail_call を実装する")


def gen_tail_call(cg, node):
    """Step 2: 末尾呼び出しを「引数の詰め替え + ジャンプ」として生成する。

    方針:
    1. すべての引数を先に評価して退避する
       for arg in node.operand.args: cg.codegen(arg); cg._push_a0()
       (先に評価しないと、f(n-1, acc+n) のように引数どうしが
        古い値を参照している場合に壊れる)
    2. 逆順に a0..a{n-1} へ取り出す
       for i in reversed(range(n)): cg._pop_into(f'a{i}')
    3. 引数スロットへ書き戻す
       param_offsets(cg) の i 番目 (名前, off) に対して
       '  sd a{i}, {off}(s0)'
    4. cg.tc_label へ j で戻る(フレームは作り直さない)
    """
    raise NotImplementedError("Step 2: gen_tail_call を実装する")
