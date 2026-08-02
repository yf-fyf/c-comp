# RV64 リファレンス

コード生成中に引くための、ターゲットアーキテクチャと呼び出し規約のまとめ。

---

## ターゲットアーキテクチャ

RISC-V RV64IM（整数 + M拡張、C拡張なし・全命令 32bit 固定長）。

RV64 を選ぶ理由（可変長命令や暗黙のフラグレジスタがないこと）は、
開発リポジトリの `design/curriculum.md` にある RISC-V 導入戦略に書いてある。

## 呼び出し規約

| 役割 | レジスタ |
|------|---------|
| 引数 | `a0`–`a7`（第1引数が `a0`） |
| 戻り値 | `a0` |
| フレームポインタ | `s0` |
| リンクレジスタ | `ra` |
| callee-saved | `s0`–`s11`（使うなら関数の入口で退避する） |
| caller-saved | `t0`–`t6`、`a0`–`a7`（関数呼び出しをまたいで保持されない） |

通常回で扱うのは、8個以下の整数引数を持つ関数の呼び出しまでである。
本格的な呼び出し規約には、この範囲の外に次のような話題がある。

| 話題 | 内容 | 扱い |
|------|------|------|
| 9個以上の引数 | `a0`–`a7` に入りきらない分はスタックで渡す | 扱わない |
| 可変長引数 | `printf` のように引数個数が変わる関数 | 発展課題 [L3](../advanced/L3_variadic/README.md) |
| 型チェック | 宣言と呼び出しの引数個数・型が一致するか確認する | 発展課題 [Q1](../advanced/Q1_typecheck/README.md) |
| 外部関数呼び出し | libc の `printf` や `malloc` を呼ぶ | コマ11・コマ13 |
| caller-saved / callee-saved | 呼び出し前後でどのレジスタを誰が保存するか | 上表の `a0`–`a7`・`ra`・`s0` の基本だけ |
| 末尾呼び出し最適化 | `return f(x);` をジャンプに変える最適化 | 発展課題 [B3](../advanced/B3_tailcall/README.md) |

## スタックフレーム

スタックポインタ `sp` は、**`call` を出す時点で 16 バイト境界**に揃っている必要がある。
違反すると `Illegal instruction` や `Bus error` として現れ、原因の特定が難しい。
qemu は 8 バイトのずれを黙って通してしまうことがあるので、
「テストが通る」ことは揃っている証拠にならない。

```python
def align_to(n, align):
    return (n + align - 1) // align * align

frame_size = align_to(self._stack_offset, 16)   # 必ずこれを使う
```

`sp` を動かす場所は2つあり、揃える責任の持ち方が異なる。

| 箇所 | 対象 |
|------|------|
| 関数のプロローグ | フレームサイズ。`align_to(_stack_offset, 16)` を通すので常に 16 の倍数（コマ4 以降） |
| `call` を出す直前 | そのとき積んでいる一時値（`_push_a0()` の分、1個 8 バイト）。奇数個なら 8 詰める（コマ7 以降） |

プロローグが常に 16 の倍数である以上、`call` 時にずれる原因は一時値の積み方だけである。
引数の個数ではないことに注意する。引数は `call` の前にレジスタへ移して `sp` を戻すため、
`call` の時点では消えている。残るのは呼び出しを囲む式が積んだ分である
（例: `n * fact(n - 1)` は `*` の左辺を1個積んだまま `fact` を呼ぶ）。

プロローグ／エピローグの形:

```asm
# プロローグ（frame_size は 16 の倍数）
  addi sp, sp, -(frame_size + 16)
  sd   ra, frame_size + 8(sp)
  sd   s0, frame_size(sp)
  addi s0, sp, frame_size + 16

# エピローグ
  ld   s0, frame_size(sp)
  ld   ra, frame_size + 8(sp)
  addi sp, sp, frame_size + 16
  ret
```

プロローグ直後、`s0` は「関数に入る前の `sp`」と同じ位置を指す。
ローカル変数は `s0` から負の方向に並ぶ（1個目が `s0-24`、2個目が `s0-32`、…）。

## よく使う命令

| 命令 | 意味 |
|------|------|
| `li rd, imm` | 即値ロード |
| `mv rd, rs` | レジスタコピー |
| `ld rd, off(rs)` / `sd rs2, off(rs1)` | 8バイトのロード / ストア |
| `lw` / `sw`、`lb` / `sb` | 4バイト / 1バイトのロード・ストア |
| `add` / `sub` / `mul` / `div` / `rem` | 算術（`div` / `rem` は M 拡張） |
| `slt` / `sltu` | 比較（小なりで1） |
| `seqz` / `snez` | 0 と等しい / 等しくない を 0/1 に |
| `and` / `or` / `xori` | 論理演算（`&&` / `\|\|` / `!`）の下位化に使う |
| `beqz rs, label` / `bnez` | 0 なら / 0 でなければ分岐 |
| `j label` / `call sym` / `ret` | 無条件ジャンプ / 関数呼び出し / 復帰 |

## 実行環境

RV64 は `qemu-riscv64`（Linux user-mode emulation）で実行する。

```bash
riscv64-linux-gnu-gcc -static hello.s -o hello
qemu-riscv64 ./hello; echo $?
```

環境の用意は [`getting_started.md`](./getting_started.md) を参照。

## 参考

- RISC-V 仕様書 Volume I (User-Level ISA) — 命令セットの一次資料
