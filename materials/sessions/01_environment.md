---
introduces:
  - rv64_asm_handwritten
  - toolchain_qemu_link
  - provided_lexer_parser
  - line_comment
  - keywords_identifiers
requires: []
---

# コマ1: 環境構築 + RV64 手書きアセンブリ

## 今日のゴール

qemu 上で手書き RV64 アセンブリを実行し、終了コード `42` を確認する。
あわせて、教員提供の Lexer/Parser で `1+2*3` の AST を表示できることも確認する。

この回ではコード生成は行わない。まずは RISC-V アセンブリを手で書いて、アセンブル・リンク・実行の流れを理解する。

## 開発環境

- Docker 環境 (`docker/rv64/`) を推奨。ネイティブ実行も許可する
- 必要なツール: `riscv64-linux-gnu-gcc`, `qemu-riscv64`

```bash
bash docker/rv64/run.sh
```

## 手書きアセンブリを動かす

### Step 1: hello.s を書く

配布される `hello.s` は終了コード `0` を返す未完成starterである。`0` を `42` に変更して、以下の内容にする。

```asm
    .global main
main:
    addi    a0, zero, 42    # 戻り値 = 42
    ret
```

### Step 2: コンパイルして実行

```bash
riscv64-linux-gnu-gcc -static hello.s -o hello
qemu-riscv64 ./hello
echo $?   # → 42
```

`42` が表示されれば成功。

![hello.s が実行されて終了コードになるまでの流れ](figures/01_toolchain.svg)

この演習で作るのは、図の hello.s にあたる「アセンブリを出力する部分」＝コンパイラ本体である。
コマ3 以降は、この部分を自作コンパイラ `mycc.py` が出力するようになる。

### Step 3: 確認スクリプト

```bash
python3 sessions/01_environment/check.py
```

### Step 4: もっと複雑な計算

`tests/` には完成済みの命令例が置いてある（一覧は後の「tests/」節を参照）。
編集対象ではないので、`addi` / `li` / `add` などの基本命令の組み合わせを読んで確認する。

## スキャフォールドの動作確認

教員提供の Lexer/Parser が AST を正しく構築できることを確認する。

```bash
python3 scaffold/parse_viewer.py sessions/02_interpreter/tests/add_mul.c
```

以下のような S 式が表示されれば成功。

```lisp
(program
  (funcdef "main" :type int (params)
    (block
      (return
        (add (num 1)
          (mul (num 2) (num 3)))))))
```

`1 + 2 * 3` が `(add (num 1) (mul (num 2) (num 3)))` のように、
掛け算が先にまとめられている（演算子の優先順位が正しく反映されている）ことを確認する。

S 式ではなく木の形で見たいときは、[AST ビジュアライザ](../../tools/app.html?mode=build) に同じソースを貼るとブラウザ上に構文木が表示され、ノードとソース範囲の対応も確認できる。

## 編集するファイル

- `hello.s`

最初に `addi a0, zero, 0` を終了コード `42` を返す命令へ変更する。

## tests/

| ファイル | 内容 | 期待値 |
|----------|------|--------|
| `hello.s` | `addi a0, zero, 42` で戻り値 42 を返す（編集する `hello.s` の完成形） | 42 |
| `sub.s` | `50 + (-8)` で減算相当 | 42 |
| `three_numbers.s` | `10 + 20 + 12` で 3 数の和 | 42 |

`sub.s` と `three_numbers.s` は完成済みの命令例であり、編集対象ではない。

## テスト

```bash
python3 sessions/01_environment/check.py
```

このコマンドは、編集した `hello.s`、完成済みの追加例2件、`1 + 2 * 3` の AST 構造をまとめて確認する。

個別に動かす場合は、次のようにする。

```bash
riscv64-linux-gnu-gcc -static sessions/01_environment/hello.s -o out

qemu-riscv64 ./out
echo $?
```

終了コードが `42` になれば成功である。

## 注意

この回ではコンパイラのコードは書かない。`mycc.py` を書き始めるのはコマ2 からである。

終了コードは 0〜255 の範囲しか返せない。
`echo $?` の値が合わないときは、`a0` に値を入れる命令が `ret` より前にあるか、
`ret` を書き忘れていないかを確認する。

`.global main` を消すとリンクに失敗する。libc の起動処理が `main` を呼ぶためである。
