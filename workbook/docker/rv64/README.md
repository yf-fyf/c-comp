# RV64 Docker 環境

演習用の RISC-V 実行環境。基本的な使い方は
[`../../docs/getting_started.md`](../../docs/getting_started.md) にある。
ここには設定とトラブルシュートだけを書く。

---

## 構成

| ファイル | 役割 |
|----------|------|
| `Dockerfile` | Ubuntu ベースに Python 3、RV64 クロスコンパイラ、qemu、gdb-multiarch を入れる |
| `run.sh` | イメージをビルドしてコンテナを起動する。`workbook/` を `/work` にマウントする |

`run.sh` は毎回 `docker build` を呼ぶが、Docker のキャッシュが効くため
2回目以降は短時間で起動できる。

## 前提条件

- Docker がインストールされていること
- 現在のユーザーで Docker を実行できること（`docker ps` が権限エラーにならない）
- 作業ディレクトリが `workbook/` であること

## イメージ名を変える

デフォルトのイメージ名は `incremental-c-rv64:latest`。
環境変数 `IMAGE` で変更できる。

```bash
IMAGE=my-rv64-env:dev bash docker/rv64/run.sh
```

## 単発コマンドの実行

`run.sh` に引数を渡すと、その1コマンドだけを実行して終了する。

```bash
bash docker/rv64/run.sh riscv64-linux-gnu-gcc --version
```

## よくあるエラー

**`permission denied while trying to connect to the docker API at unix:///var/run/docker.sock`**

Docker デーモンへのアクセス権が不足している。
Docker グループの設定、または sudo 経由の実行を確認する。

**マウントしたファイルが見えない / 変更が反映されない**

`run.sh` は `workbook/` を `/work` にマウントする。
`workbook/` の外にあるファイル（`materials/` など）はコンテナから見えない。

## ネイティブ実行に切り替える

Docker を使わない場合、ホストに次が必要になる。

- `python3`（3.10 以降）
- `riscv64-linux-gnu-gcc`（RV64 クロスコンパイラ）
- `qemu-riscv64`
- `gdb-multiarch`（デバッグする場合）

インストール方法はディストリビューションによって異なる。
`Dockerfile` に入れているパッケージ名が参考になる。
