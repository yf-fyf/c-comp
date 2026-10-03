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

## 必要なもの

配布物の親ディレクトリから `cd workbook` で移動し、
`ls sessions/00_setup/hello.s docker/rv64/run.sh` で作業場所を確認する。
以降のコマンドは `workbook/` から実行する。

- **Python 3.10 以降**（`match` 文、`str | None` のような合併型注釈を使う）。
  Docker 環境・ネイティブ実行のどちらでも必要になる基準である
- RV64 クロスコンパイラ `riscv64-linux-gnu-gcc`
- `qemu-riscv64`

環境要件の出典は資料原稿 `materials/sessions/00_setup.md`（上記の資料サイトの元になっている）である。
WSL の導入手順を含む詳しい説明は上記の資料サイトにある。

推奨は Docker で、上の3つが入った環境が用意してある（`workbook/` から実行する）。
macOSでは、[Docker公式の手順](https://docs.docker.com/desktop/setup/install/mac-install/)
に従い自分のMacに合うDocker Desktopを入れて起動する。
ホストのターミナルで `docker ps` がコンテナ一覧を表示すれば準備完了である。

Ubuntu（WSL の中でも同じ）では、Docker がまだ無い場合に次を実行して入れる。

```bash
sudo apt update
sudo apt install -y curl
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

`usermod` の後は一度ログアウトして入り直す（`docker ps` が権限エラーにならなければ準備完了）。

```bash
# コンテナ起動（初回はイメージをビルド）
bash docker/rv64/run.sh

# 完成済みの命令例で実行環境だけを確認する
bash docker/rv64/run.sh sh -c 'riscv64-linux-gnu-gcc -static sessions/00_setup/tests/sub.s -o /tmp/rv64_smoke && qemu-riscv64 /tmp/rv64_smoke'
echo $?   # → 42
```

ネイティブ実行も許可する。Ubuntu なら次で入る。

```bash
sudo apt install gcc-riscv64-linux-gnu qemu-user python3
```

イメージ名の変更やよくあるエラーは [`../../docker/rv64/README.md`](../../docker/rv64/README.md) を参照。

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

Dockerを使う場合は、上のコマンドを `bash docker/rv64/run.sh` で開いたシェルから実行するか、
ホストから `bash docker/rv64/run.sh python3 sessions/00_setup/check.py` と指定する。

このコマンドは、編集した `hello.s` と完成済みの追加例2件をまとめて確認する。
`[PASS]` が3件表示され、終了コードが `0` になればこの回は完了である。
編集前のstarterでは `hello.s` だけが `[FAIL]` となり、終了コードは `1` になる。

手動で確認する場合（Dockerではコンテナ内の `/work`、ネイティブでは `workbook/` から）:

```bash
riscv64-linux-gnu-gcc -static sessions/00_setup/hello.s -o /tmp/hello_rv64
qemu-riscv64 /tmp/hello_rv64
echo $?
```

`42` が表示されれば成功。

全3件の確認が済んだら、[コマ1のREADME](../01_interpreter/README.md)へ進む。
