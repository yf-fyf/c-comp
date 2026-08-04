#!/usr/bin/env python3
"""L5 確認スクリプト — byval.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの byval.py
    python3 check.py path/to/passes_dir

この回のテストは、出た命令列を**小さな RV64 シミュレータで実際に走らせる**。
「値渡し・値返し」は「コピーが本当に起きたか」「元が無傷か」という
メモリの性質なので、命令の並びを見比べるだけでは確かめきれないからである。
"""

import importlib.util
import re
import sys
import types
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


comp = load("L5_byval", passes_dir / "byval.py")
langcc = load("L5_langcc", DIR / "langcc.py")

sys.path.insert(0, str(SCAFFOLD))   # scaffold の lexer / parser を使う

pass_count = 0
fail_count = 0
skip_count = 0

_shims = {}


def shims():
    """構文の shim を1度だけ作る(字句は標準トラックのまま)。"""
    if not _shims:
        import lexer
        import parser as real_parser
        _shims['lexer'] = lexer
        _shims['parser'] = langcc.install_parser_shim(real_parser)
    return _shims


def expr(src):
    toks = shims()['lexer'].tokenize(src)
    return shims()['parser'].Parser(toks).parse_expr()


def program(src):
    toks = shims()['lexer'].tokenize(src)
    return shims()['parser'].parse(toks)


def ret_stmt(src):
    """`return 式;` に相当する Return ノードを作る(operand だけ使われる)。"""
    return types.SimpleNamespace(kind='Return', operand=expr(src))


# ---- 小さな RV64 シミュレータ -------------------------------------------

WIDTH = {'ld': 8, 'sd': 8, 'lw': 4, 'lwu': 4, 'sw': 4,
         'lh': 2, 'lhu': 2, 'sh': 2, 'lb': 1, 'lbu': 1, 'sb': 1}
LOADS = ('ld', 'lw', 'lwu', 'lh', 'lhu', 'lb', 'lbu')

MEM_RE = re.compile(r'^(\w+)\s+(\w+)\s*,\s*(-?\d+)\s*\(\s*(\w+)\s*\)$')
ADDI_RE = re.compile(r'^addi\s+(\w+)\s*,\s*(\w+)\s*,\s*(-?\d+)$')
MV_RE = re.compile(r'^mv\s+(\w+)\s*,\s*(\w+)$')
LI_RE = re.compile(r'^li\s+(\w+)\s*,\s*(-?\d+)$')


class Unsupported(Exception):
    """シミュレータが知らない命令。実装が想定外の道を通っている合図。"""


class Machine:
    """ld/sd・lw/sw・lb/sb・addi・mv・li だけを解釈する。"""

    SIZE = 8192

    def __init__(self, s0):
        self.mem = bytearray(self.SIZE)
        self.regs = {'s0': s0, 'sp': self.SIZE - 64}
        self.stored = set()          # 書き込んだアドレス(はみ出し検出用)

    # --- メモリ ---

    def put(self, addr, data):
        self.mem[addr:addr + len(data)] = data

    def get(self, addr, size):
        return bytes(self.mem[addr:addr + size])

    def put_word(self, addr, value):
        self.put(addr, value.to_bytes(8, 'little', signed=False))

    def get_word(self, addr):
        return int.from_bytes(self.get(addr, 8), 'little', signed=False)

    # --- 実行 ---

    def run(self, lines):
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            self.step(line)
        return self

    def step(self, line):
        m = MEM_RE.match(line)
        if m and m.group(1) in WIDTH:
            op, rd, off, rs = m.group(1), m.group(2), int(m.group(3)), m.group(4)
            addr = self.regs.get(rs, 0) + off
            n = WIDTH[op]
            if not 0 <= addr <= self.SIZE - n:
                raise Unsupported(f"範囲外のアドレスに触った: {line}")
            if op in LOADS:
                signed = op in ('ld', 'lw', 'lh', 'lb')
                self.regs[rd] = int.from_bytes(self.get(addr, n), 'little',
                                               signed=signed)
            else:
                value = self.regs.get(rd, 0) & ((1 << 64) - 1)
                self.put(addr, value.to_bytes(8, 'little')[:n])
                self.stored.update(range(addr, addr + n))
            return
        m = ADDI_RE.match(line)
        if m:
            self.regs[m.group(1)] = self.regs.get(m.group(2), 0) + int(m.group(3))
            return
        m = MV_RE.match(line)
        if m:
            self.regs[m.group(1)] = self.regs.get(m.group(2), 0)
            return
        m = LI_RE.match(line)
        if m:
            self.regs[m.group(1)] = int(m.group(2))
            return
        raise Unsupported(f"シミュレータの知らない命令: '{line}'")


# ---- 偽コード生成器 ------------------------------------------------------

S0 = 4096                  # フレームの基準(s0)
CALLER = 1024              # 「呼び出し元のフレーム」に見立てた領域の先頭

STRUCTS = {
    'struct Point': 8,     # int x; int y;
    'struct Box': 12,      # int w; int h; int d;
    'struct Acc': 8,
    'struct Small': 5,     # 端数バイトのコピーを見るための合成フィクスチャ
    'struct Big': 16,
}

STRUCT_RET = {'make': 'struct Point', 'add': 'struct Point',
              'step': 'struct Acc', 'scale': 'struct Box'}


class FakeCG:
    """本物のコード生成器の代わり。

    codegen / codegen_lval は「その式のアドレスを a0 に置く」ことを
    li a0, <番地> で真似る。呼び出しでレジスタが壊れる状況も再現できる。
    """

    VARS = {'p': 'struct Point', 'q': 'struct Point', 'r': 'struct Acc',
            'b': 'struct Box', 'sm': 'struct Small',
            'ptr': 'struct Point*', 'i': 'int', 'c': 'char'}
    MEMBERS = {'x': 'int', 'y': 'int', 'w': 'int', 'h': 'int', 'd': 'int',
               'n': 'int', 'sum': 'int'}

    def __init__(self, params=(), ret_ty='int', offsets=None,
                 sret=None, sret_slots=None, addrs=None, clobber=False):
        self.lines = []
        self.params = list(params)
        self.ret_ty = ret_ty
        self.offsets = dict(offsets or {})
        self.sret = sret                      # (引数レジスタ番号, オフセット)
        self.sret_slots = dict(sret_slots or {})   # ノード id → オフセット
        self.addrs = dict(addrs or {})             # ノード id → 番地
        self.clobber = clobber                # codegen が a1/a2 を壊す関数呼び出しか
        self.codegen_calls = 0
        self.lval_calls = 0
        self.calls = []                       # emit_call の記録
        self.codegen_end = -1                 # 最後に codegen が終わった行番号

    # --- 学習者が使ってよい部品 ---

    def emit(self, line):
        self.lines.append(line.strip())

    def _place(self, node):
        if self.clobber:
            # 関数呼び出しなら引数レジスタは壊れている、という最悪の場合を再現する
            self.emit('  li a1, 0')
            self.emit('  li a2, 0')
        self.emit(f'  li a0, {self.addrs.get(id(node), 0)}')
        self.codegen_end = len(self.lines) - 1

    def codegen(self, node):
        self.codegen_calls += 1
        self._place(node)

    def codegen_lval(self, node):
        self.lval_calls += 1
        self._place(node)

    def _push_a0(self):
        self.emit('push a0')

    def _pop_into(self, reg):
        self.emit(f'pop {reg}')

    def struct_size(self, ty):
        return STRUCTS.get(ty)

    def expr_type(self, node):
        kind = node.kind
        if kind == 'Var':
            return self.VARS.get(node.name, 'int')
        if kind == 'Deref':
            inner = self.expr_type(node.operand)
            return inner[:-1] if inner.endswith('*') else inner
        if kind == 'Member':
            return self.MEMBERS.get(node.name, 'int')
        if kind == 'Call':
            return STRUCT_RET.get(node.name, 'int')
        if kind == 'Addr':
            return self.expr_type(node.operand) + '*'
        return 'int'

    def frame_offset(self, name):
        return self.offsets[name]

    def current_params(self):
        return list(self.params)

    def current_ret_type(self):
        return self.ret_ty

    def sret_param(self):
        return self.sret

    def sret_slot_addr(self, node):
        self.emit(f'  addi a0, s0, {self.sret_slots[id(node)]}')

    def emit_call(self, name, nargs):
        self.calls.append((name, nargs))
        self.emit(f'  call {name}')


def check(label, ok, detail=""):
    global pass_count, fail_count
    if ok:
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        print(f"  [FAIL] {label}{(' — ' + detail) if detail else ''}")
        fail_count += 1


def run_step(name, fn):
    global skip_count, fail_count
    print(f"--- {name} ---")
    try:
        fn()
    except NotImplementedError as e:
        print(f"  [SKIP] 未実装: {e}")
        skip_count += 1
    except Unsupported as e:
        print(f"  [FAIL] {e}")
        fail_count += 1


def stores(lines):
    return [l for l in lines if l.split()[0] in ('sd', 'sw', 'sh', 'sb')]


# ---- 構文(langcc.py が用意済み。実装前でも通る) ----

SRC = """
struct Point { int x; int y; };
struct Point make(int x, int y) { struct Point p; p.x = x; p.y = y; return p; }
int sum(struct Point p) { return p.x + p.y; }
int main() { return sum(make(3, 4)); }
"""


def syntax():
    nodes = program(SRC)
    by_name = {n.name: n for n in nodes}

    check("struct 値の仮引数を受理する(param ::= obj_type IDENT)",
          by_name['sum'].params[0].ty_str == 'struct Point',
          by_name['sum'].params[0].ty_str)
    check("struct 値の戻り値を受理する(ret_type に 'struct' IDENT を足した)",
          by_name['make'].ty_str == 'struct Point', by_name['make'].ty_str)
    check("struct 値を返す関数は STRUCT_RET_FUNCS に載る",
          langcc.STRUCT_RET_FUNCS.get('make') == 'struct Point',
          str(langcc.STRUCT_RET_FUNCS))
    check("struct 値を返さない関数は載らない",
          'sum' not in langcc.STRUCT_RET_FUNCS and
          'main' not in langcc.STRUCT_RET_FUNCS,
          str(langcc.STRUCT_RET_FUNCS))
    check("ポインタの仮引数・戻り値は従来どおり",
          program("struct Point *f(struct Point *p) { return p; }")[0].ty_str
          == 'struct Point*')


# ---- Step 1: copy_struct ----

def copy(size, src=CALLER, dst=CALLER + 512, pattern=None):
    """copy_struct を走らせ、(cg, machine) を返す。"""
    cg = FakeCG()
    comp.copy_struct(cg, size)
    m = Machine(S0)
    data = pattern or bytes((i * 7 + 3) & 0xFF for i in range(size))
    m.put(src, data)
    m.put(dst - 8, b'\xEE' * (size + 16))     # 前後に番人を置く
    m.put(dst, b'\xEE' * size)
    m.regs['a0'] = src
    m.regs['a1'] = dst
    m.run(cg.lines)
    return cg, m, data


def step1():
    for size in (1, 4, 5, 8, 12, 16):
        cg, m, data = copy(size)
        dst = CALLER + 512
        check(f"{size} バイトが全部写る",
              m.get(dst, size) == data, m.get(dst, size).hex())
        check(f"{size} バイト: 写す範囲の外を壊さない",
              m.get(dst - 8, 8) == b'\xEE' * 8
              and m.get(dst + size, 8) == b'\xEE' * 8,
              m.get(dst - 8, size + 16).hex())
        check(f"{size} バイト: 元(a0 の指す先)は無傷",
              m.get(CALLER, size) == data)
        check(f"{size} バイト: a0 と a1 を壊さない",
              m.regs['a0'] == CALLER and m.regs['a1'] == dst,
              f"a0={m.regs['a0']} a1={m.regs['a1']}")

    # 大きい単位から使えば命令数はこうなる(1 バイトずつだと通らない)
    for size, want in ((1, 1), (4, 1), (5, 2), (8, 1), (12, 2), (16, 2)):
        cg, _, _ = copy(size)
        n = len(stores(cg.lines))
        check(f"{size} バイトは store {want} 回で済ませる(大きい単位から)",
              n == want, f"{n} 回: {cg.lines}")

    cg, _, _ = copy(8)
    check("8 バイトは ld / sd の 2 命令",
          cg.lines == ['ld a2, 0(a0)', 'sd a2, 0(a1)'], str(cg.lines))


# ---- Step 2: gen_arg ----

def one_arg(src, addrs_for=None):
    node = expr(src)
    cg = FakeCG(addrs={id(node): CALLER})
    comp.gen_arg(cg, node)
    return cg, node


def step2():
    for src, label in (("p", "struct 変数"),
                       ("*ptr", "*p(ポインタの指す先)"),
                       ("make(1, 2)", "struct 値を返す呼び出し")):
        cg, _ = one_arg(src)
        check(f"{label} はアドレスを渡す(codegen_lval)",
              cg.lval_calls == 1 and cg.codegen_calls == 0,
              f"lval={cg.lval_calls} codegen={cg.codegen_calls}")

    for src, label in (("i", "int 変数"),
                       ("ptr", "struct へのポインタ"),
                       ("p.x", "struct のメンバ(int)"),
                       ("i + 1", "式"),
                       ("sum(p)", "int を返す呼び出し")):
        cg, _ = one_arg(src)
        check(f"{label} は従来どおり値を渡す(codegen)",
              cg.codegen_calls == 1 and cg.lval_calls == 0,
              f"lval={cg.lval_calls} codegen={cg.codegen_calls}")

    cg, _ = one_arg("p")
    check("引数1個ぶんで評価は1回だけ(コピーは呼ばれ側の仕事)",
          cg.codegen_calls + cg.lval_calls == 1,
          f"{cg.codegen_calls + cg.lval_calls} 回")
    check("呼び出し側は構造体をコピーしない(store を出さない)",
          stores(cg.lines) == [], str(cg.lines))


# ---- Step 3: gen_param_prologue ----

def prologue(params, ret_ty='int', sret=None, offsets=None):
    cg = FakeCG(params=params, ret_ty=ret_ty, offsets=offsets, sret=sret)
    comp.gen_param_prologue(cg)
    return cg


def step3():
    # (a) struct 仮引数 1 個 + int 仮引数 1 個。struct 値は返さない
    params = [(0, 'p', 'struct Point'), (1, 'k', 'int')]
    offs = {'p': -8, 'k': -16}
    cg = prologue(params, offsets=offs)

    m = Machine(S0)
    caller = bytes([1, 0, 0, 0, 2, 0, 0, 0])       # x=1, y=2
    m.put(CALLER, caller)
    m.put_word(S0 - 8, CALLER)                     # プロローグが書いた「アドレス」
    m.put_word(S0 - 16, 99)                        # int 仮引数はそのまま
    m.run(cg.lines)

    check("struct 仮引数がフレーム内へ複製される",
          m.get(S0 - 8, 8) == caller, m.get(S0 - 8, 8).hex())
    check("int の仮引数には触らない",
          m.get_word(S0 - 16) == 99, str(m.get_word(S0 - 16)))

    # 値渡しの意味論: 呼ばれ側が仮引数を書き換えても呼び出し元は変わらない
    m.put(S0 - 8, bytes([100, 0, 0, 0, 2, 0, 0, 0]))
    check("呼ばれ側の変更が呼び出し元に伝わらない(これが値渡し)",
          m.get(CALLER, 8) == caller, m.get(CALLER, 8).hex())
    # 逆向き: 呼び出し元をあとから書き換えても仮引数は変わらない
    m.put(CALLER, bytes([7, 0, 0, 0, 7, 0, 0, 0]))
    check("呼び出し元の変更が呼ばれ側に伝わらない",
          m.get(S0 - 8, 8) == bytes([100, 0, 0, 0, 2, 0, 0, 0]),
          m.get(S0 - 8, 8).hex())

    # (b) int 仮引数だけ・struct も返さない → 何も出ない
    cg = prologue([(0, 'k', 'int'), (1, 'j', 'int')], offsets={'k': -8, 'j': -16})
    check("struct が絡まない関数では1命令も出ない", cg.lines == [], str(cg.lines))

    # (c) struct 仮引数 2 個 + struct 値を返す(nested.c の add と同じ形)
    params = [(0, 'a', 'struct Point'), (1, 'b', 'struct Point')]
    offs = {'a': -8, 'b': -16, '.sretp': -24}
    cg = prologue(params, ret_ty='struct Point', sret=(2, -24), offsets=offs)

    check("隠しポインタの退避が先頭に来る(copy_struct がレジスタを壊す前)",
          bool(cg.lines) and cg.lines[0] == 'sd a2, -24(s0)', str(cg.lines[:2]))

    m = Machine(S0)
    a_data = bytes([1, 0, 0, 0, 2, 0, 0, 0])
    b_data = bytes([3, 0, 0, 0, 4, 0, 0, 0])
    m.put(CALLER, a_data)
    m.put(CALLER + 64, b_data)
    m.put_word(S0 - 8, CALLER)
    m.put_word(S0 - 16, CALLER + 64)
    m.regs['a0'] = CALLER
    m.regs['a1'] = CALLER + 64
    m.regs['a2'] = CALLER + 128            # 呼び出し側が渡した隠しポインタ
    m.run(cg.lines)

    check("2 個目の struct 仮引数も複製される",
          m.get(S0 - 8, 8) == a_data and m.get(S0 - 16, 8) == b_data,
          f"{m.get(S0 - 8, 8).hex()} / {m.get(S0 - 16, 8).hex()}")
    check("隠しポインタが .sretp に残っている(a2 を壊す前に退避できている)",
          m.get_word(S0 - 24) == CALLER + 128, str(m.get_word(S0 - 24)))
    check("呼び出し元の 2 個の構造体はどちらも無傷",
          m.get(CALLER, 8) == a_data and m.get(CALLER + 64, 8) == b_data)

    # (d) struct 値を返すが struct 仮引数は無い
    cg = prologue([(0, 'k', 'int')], ret_ty='struct Point', sret=(1, -16),
                  offsets={'k': -8, '.sretp': -16})
    check("struct 仮引数が無くても隠しポインタは退避する",
          cg.lines == ['sd a1, -16(s0)'], str(cg.lines))

    # (e) 12 バイト(inout.c の Box)でも通る
    cg = prologue([(0, 'b', 'struct Box')], offsets={'b': -16})
    m = Machine(S0)
    box = bytes([1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0])
    m.put(CALLER, box)
    m.put_word(S0 - 16, CALLER)
    m.run(cg.lines)
    check("12 バイトの struct 仮引数も全部写る",
          m.get(S0 - 16, 12) == box, m.get(S0 - 16, 12).hex())


# ---- Step 4: gen_sret_call ----

def sret_call(src, slot=-32):
    node = expr(src)
    addrs = {id(a): CALLER + 8 * k for k, a in enumerate(node.args)}
    cg = FakeCG(sret_slots={id(node): slot}, addrs=addrs)
    comp.gen_sret_call(cg, node)
    return cg, node, slot


def step4():
    cg, node, slot = sret_call("make(3, 4)")
    pushes = [i for i, l in enumerate(cg.lines) if l == 'push a0']
    call = [i for i, l in enumerate(cg.lines) if l.startswith('call ')]

    check("emit_call を1回だけ呼ぶ", len(call) == 1, str(cg.lines))
    if not call:
        return
    call = call[0]

    check("引数は 2 個 + 隠しポインタ 1 個 = 3 個積む",
          len(pushes) == 3, f"{len(pushes)} 個: {cg.lines}")
    check("emit_call には (関数名, 引数の個数 + 1) を渡す",
          cg.calls == [('make', 3)], str(cg.calls))
    check("ユーザ引数を 2 個とも生成する",
          cg.codegen_calls + cg.lval_calls == 2,
          f"{cg.codegen_calls + cg.lval_calls} 回")

    sret_lines = [i for i, l in enumerate(cg.lines) if l == f'addi a0, s0, {slot}']
    check("戻り先のアドレスを sret_slot_addr で取る(自前で計算しない)",
          len(sret_lines) == 2, str(cg.lines))
    if len(sret_lines) == 2:
        check("隠しポインタは **末尾** に積む(実 ABI の a0 先頭とは違う)",
              sret_lines[0] < call and pushes[-1] > sret_lines[0]
              and pushes[-1] == sret_lines[0] + 1,
              str(cg.lines))
        check("呼び出しの **後** にもう一度戻り先のアドレスを a0 に載せ直す",
              sret_lines[1] > call, str(cg.lines))
    check("この式の値は戻り先のアドレス(最後の行がそれ)",
          cg.lines[-1] == f'addi a0, s0, {slot}', str(cg.lines[-3:]))

    # 引数 0 個(隠しポインタだけ)
    cg0, _, slot0 = sret_call("now()")
    check("引数 0 個でも隠しポインタ 1 個は積む",
          cg0.calls == [('now', 1)], str(cg0.calls))

    # struct 値の実引数は Step 2 を通る(アドレス渡し)
    node = expr("add(p, q)")
    addrs = {id(a): CALLER + 8 * k for k, a in enumerate(node.args)}
    cg2 = FakeCG(sret_slots={id(node): -40}, addrs=addrs)
    comp.gen_sret_call(cg2, node)
    check("struct 値の実引数は gen_arg 経由でアドレスを渡す",
          cg2.lval_calls == 2 and cg2.codegen_calls == 0,
          f"lval={cg2.lval_calls} codegen={cg2.codegen_calls}")
    check("呼び出し側は戻り値も引数もコピーしない(store を出さない)",
          stores(cg2.lines) == [], str(cg2.lines))


# ---- Step 5: gen_struct_return ----

def struct_return(src, ret_ty, sret_off=-24, clobber=True, addr=CALLER):
    node = ret_stmt(src)
    cg = FakeCG(ret_ty=ret_ty, sret=(0, sret_off), offsets={'.sretp': sret_off},
                addrs={id(node.operand): addr}, clobber=clobber)
    comp.gen_struct_return(cg, node)
    return cg, node


def step5():
    RECV = CALLER + 512        # 呼び出し側が用意した受け取り領域
    cg, _ = struct_return("p", 'struct Point')

    m = Machine(S0)
    local = bytes([5, 0, 0, 0, 6, 0, 0, 0])
    m.put(CALLER, local)
    m.put(RECV, b'\xEE' * 16)
    m.put_word(S0 - 24, RECV)                  # Step 3 が退避した隠しポインタ
    m.run(cg.lines)

    check("返す構造体が呼び出し側の領域へ写る",
          m.get(RECV, 8) == local, m.get(RECV, 8).hex())
    check("写す範囲の外を壊さない",
          m.get(RECV + 8, 8) == b'\xEE' * 8, m.get(RECV + 8, 8).hex())
    check("a0 には戻り先のアドレスを残す(呼び出し側がそこを読む)",
          m.regs.get('a0') == RECV, str(m.regs.get('a0')))

    # 値返しの意味論: 返したあとで元をいじっても受け取り側は変わらない
    m.put(CALLER, bytes([9, 0, 0, 0, 9, 0, 0, 0]))
    check("呼ばれ側の局所変数の変更が受け取り側に伝わらない(これが値返し)",
          m.get(RECV, 8) == local, m.get(RECV, 8).hex())

    check("隠しポインタは式を評価した **後** に読む(式が関数呼び出しでも壊れない)",
          cg.codegen_end >= 0
          and all(not l.startswith('ld ') or i > cg.codegen_end
                  for i, l in enumerate(cg.lines)),
          str(cg.lines))
    check("返す式は codegen で1回だけ評価する",
          cg.codegen_calls == 1 and cg.lval_calls == 0,
          f"codegen={cg.codegen_calls} lval={cg.lval_calls}")

    # 戻り値がそのまま関数呼び出し(recurse.c の `return step(r);`)
    cg2, _ = struct_return("step(r)", 'struct Acc', addr=CALLER + 64)
    m2 = Machine(S0)
    inner = bytes([0, 0, 0, 0, 15, 0, 0, 0])
    m2.put(CALLER + 64, inner)
    m2.put_word(S0 - 24, RECV)
    m2.put(RECV, b'\xEE' * 8)
    m2.run(cg2.lines)
    check("`return step(r);`(戻り値が戻り値になる)でも正しく写る",
          m2.get(RECV, 8) == inner, m2.get(RECV, 8).hex())
    check("`return step(r);` でも a0 は戻り先のアドレス",
          m2.regs.get('a0') == RECV, str(m2.regs.get('a0')))

    # 12 バイト
    cg3, _ = struct_return("b", 'struct Box')
    m3 = Machine(S0)
    box = bytes([1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0])
    m3.put(CALLER, box)
    m3.put(RECV, b'\xEE' * 16)
    m3.put_word(S0 - 24, RECV)
    m3.run(cg3.lines)
    check("12 バイトの戻り値も全部写る",
          m3.get(RECV, 12) == box, m3.get(RECV, 12).hex())
    check("12 バイトでも 12 バイトを超えて書かない",
          m3.get(RECV + 12, 4) == b'\xEE' * 4, m3.get(RECV + 12, 4).hex())


run_step("構文: struct 値の仮引数・戻り値(langcc.py が用意済み)", syntax)
run_step("Step 1: copy_struct(コピーの土台)", step1)
run_step("Step 2: gen_arg(呼び出し側 — アドレスを渡す)", step2)
run_step("Step 3: gen_param_prologue(呼ばれ側 — フレーム内へ複製)", step3)
run_step("Step 4: gen_sret_call(呼び出し側 — 隠しポインタを末尾に)", step4)
run_step("Step 5: gen_struct_return(呼ばれ側 — 隠しポインタの先へ)", step5)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
