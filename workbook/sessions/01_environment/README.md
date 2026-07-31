# コマ1: 環境構築 + RV64 手書きアセンブリ

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/01_environment/](https://yf-fyf.github.io/c-comp/sessions/01_environment/) にあります。

## 今日のゴール

qemu 上で手書き RV64 アセンブリを実行し、終了コード `42` を確認する。
あわせて、教員提供の Lexer/Parser で `1 + 2 * 3` の AST を表示できることも確認する。
この回ではコード生成は行わない。

## 実装する主な機能

- `hello.s` を編集し、終了コード `42` を返す命令を書く
- アセンブル・リンク・実行の流れ（`riscv64-linux-gnu-gcc -static` でのアセンブル・リンク → `qemu-riscv64` での実行）を体験する
- 教員提供の Lexer/Parser で `1 + 2 * 3` の AST 構造を表示して確認する

## 編集するファイル

- `hello.s` の `addi a0, zero, 0` を、終了コード `42` を返す命令に変更する。

## テスト

`tests/sub.s` と `tests/three_numbers.s` は完成済みの命令例であり、編集対象ではない。

| ファイル | 内容 | 期待値 |
|----------|------|--------|
| `tests/hello.s` | `addi a0, zero, 42` で戻り値 42 を返す | 42 |
| `tests/sub.s` | `50 + (-8)` で減算相当 | 42 |
| `tests/three_numbers.s` | `10 + 20 + 12` で 3 数の和 | 42 |

```bash
python3 sessions/01_environment/check.py
```

このコマンドは、編集した `hello.s`、完成済みの追加例2件、`1 + 2 * 3` の AST 構造をまとめて確認する。

手動で確認する場合:

```bash
riscv64-linux-gnu-gcc -static sessions/01_environment/hello.s -o /tmp/hello_rv64
qemu-riscv64 /tmp/hello_rv64
echo $?
```

`42` が表示されれば成功。
