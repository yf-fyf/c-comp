# コマ0: 演習環境構築

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/00_setup/](https://yf-fyf.github.io/c-comp/sessions/00_setup/) にあります。

授業開始前に自分で進めておく回である。番号のある通常回には含めない。

## ゴール

演習に使う環境（Python・RV64 クロスコンパイラ・qemu）を用意し、
qemu 上で手書き RV64 アセンブリを実行して終了コード `42` を確認する。
この回ではコンパイラのコードは書かない。

## やること

- Windows の場合は WSL 上に Ubuntu を入れる
- Docker 環境（推奨）またはネイティブ実行の環境を用意する
- `hello.s` を編集し、終了コード `42` を返す命令を書く
- アセンブル・リンク・実行の流れ（`riscv64-linux-gnu-gcc -static` でのアセンブル・リンク → `qemu-riscv64` での実行）を体験する

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
python3 sessions/00_setup/check.py
```

このコマンドは、編集した `hello.s` と完成済みの追加例2件をまとめて確認する。

手動で確認する場合:

```bash
riscv64-linux-gnu-gcc -static sessions/00_setup/hello.s -o /tmp/hello_rv64
qemu-riscv64 /tmp/hello_rv64
echo $?
```

`42` が表示されれば成功。
