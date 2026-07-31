#!/usr/bin/env python3
"""Q1: 型検査パス(スケルトン)

AST を受け取り、実行前に見つけられる誤りを集めて報告する。
コード生成には手を出さない(エラーを見つけるだけ)。

実装する順番:
    Step 1: check_var       未定義の変数
    Step 2: check_call      未定義の関数・引数の個数
    Step 3: check_assign    代入先にできない式
    Step 4: check_incdec    前置 ++/-- の対象にできない式

収集(collect)と走査(walk)は完成済み。

確認:
    python3 check.py
"""

import sys
from pathlib import Path


def _find_scaffold():
    d = Path(__file__).resolve().parent
    while d != d.parent:
        for cand in (d / "scaffold", d / "workbook" / "scaffold"):
            if (cand / "ast_def.py").is_file():
                return cand
        d = d.parent
    raise FileNotFoundError("scaffold/ が見つからない")


sys.path.insert(0, str(_find_scaffold()))

from ast_def import *  # noqa: E402,F403

CHILD_FIELDS = ['lhs', 'rhs', 'operand', 'cond', 'then', 'else_',
                'init', 'step', 'body']
LIST_FIELDS = ['stmts', 'args']


class Error:
    """見つけた誤り1件。"""

    def __init__(self, line, msg):
        self.line = line
        self.msg = msg

    def __repr__(self):
        return f"[line {self.line}] {self.msg}"

    def __eq__(self, other):
        return (self.line, self.msg) == (other.line, other.msg)


class TypeChecker:
    def __init__(self):
        self.errors = []
        self.globals = {}      # 名前 → ty_str
        self.funcs = {}        # 名前 → (引数の個数, 個数を検査してよいか)
        self.locals = {}       # 名前 → ty_str(関数ごとに作り直す)

    # ---- 収集(完成済み) ----

    def collect(self, prog):
        """トップレベルを一巡して、グローバル変数と関数の一覧を作る。"""
        for node in prog:
            if node.kind == ND_DECL:
                self.globals[node.name] = node.ty_str
            elif node.kind in (ND_FUNCDEF, ND_FUNCPROTO):
                # 個数を検査してよいのは、定義がこのプログラム内にある関数だけ。
                # 宣言だけの関数(printf など)は可変長かもしれず、
                # '...' は AST に残らないため個数を確かめられない。
                checkable = node.kind == ND_FUNCDEF
                prev = self.funcs.get(node.name)
                if prev is None or checkable:
                    self.funcs[node.name] = (len(node.params), checkable)

    def error(self, node, msg):
        self.errors.append(Error(node.line, msg))

    def lookup(self, name):
        if name in self.locals:
            return self.locals[name]
        return self.globals.get(name)

    # ---- Step 1: 変数の検査 ----

    def check_var(self, node):
        """Step 1: 変数参照 node が宣言済みかを調べる。

        方針:
        - self.lookup(node.name) が None なら未定義
        - self.error(node, f"未定義の変数: {node.name}") で報告する
        """
        raise NotImplementedError("Step 1: check_var を実装する")

    # ---- Step 2: 関数呼び出しの検査 ----

    def check_call(self, node):
        """Step 2: 関数呼び出し node を調べる。

        方針:
        - self.funcs に名前がなければ
          f"未定義の関数: {node.name}" を報告して終わる
        - あれば (引数の個数, 検査してよいか) が取れる。
          検査してよく、かつ node.args の個数が違えば
          f"関数 {node.name} の引数の個数が合いません"
          f"（宣言 {nparams} 個、呼び出し {len(node.args)} 個）"
          を報告する
        """
        raise NotImplementedError("Step 2: check_call を実装する")

    # ---- Step 3: 代入先の検査 ----

    def check_assign(self, node):
        """Step 3: 代入 node の左辺が lvalue かを調べる。

        方針: 代入先にできるのは次の4種類だけ(コマ9 の codegen_lval が
        扱えるもの)。それ以外なら
        f"代入先にできない式です（{左辺の kind}）" を報告する。
            ND_VAR / ND_DEREF / ND_INDEX / ND_MEMBER
        """
        raise NotImplementedError("Step 3: check_assign を実装する")

    # ---- Step 4: 前置 ++/-- の対象の検査 ----

    def check_incdec(self, node):
        """Step 4: 前置 ++/-- (node) の operand が lvalue かを調べる。

        方針: 対象にできるのは Step 3 の check_assign と同じ4種類だけ
        (同じ集合を再利用してよい)。それ以外なら
        f"++/-- の対象にできない式です({operand の kind})" を報告する。
            ND_VAR / ND_DEREF / ND_INDEX / ND_MEMBER
        """
        raise NotImplementedError("Step 4: check_incdec を実装する")

    # ---- 走査(完成済み) ----

    def walk(self, node):
        if node is None:
            return
        if node.kind == ND_VAR:
            self.check_var(node)
        elif node.kind == ND_CALL:
            self.check_call(node)
        elif node.kind == ND_ASSIGN:
            self.check_assign(node)
        elif node.kind in (ND_PREINC, ND_PREDEC):
            self.check_incdec(node)
        elif node.kind == ND_DECL:
            self.locals[node.name] = node.ty_str
            return
        for f in CHILD_FIELDS:
            self.walk(getattr(node, f))
        for f in LIST_FIELDS:
            for c in getattr(node, f):
                self.walk(c)

    def check_func(self, node):
        self.locals = {}
        for p in node.params:
            if p.name:
                self.locals[p.name] = p.ty_str
        self.walk(node.body)

    def check_program(self, prog):
        self.collect(prog)
        for node in prog:
            if node.kind == ND_FUNCDEF:
                self.check_func(node)
        self.errors.sort(key=lambda e: e.line)
        return self.errors


def check_program(prog):
    """AST を検査し、見つけた Error のリストを返す(完成済みの入口)。"""
    return TypeChecker().check_program(prog)
