# O2: 基本ブロックとフローグラフ

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/O2_cfg/](https://yf-fyf.github.io/c-comp/advanced/O2_cfg/) にあります。

## 今日のゴール

アセンブリを**基本ブロック**に切り分け、制御の流れを辺で結んで
**フローグラフ**を作る。Graphviz で図にして目で確かめる。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ16（完成した `final/mycc.py`）、O1（`golden.py` が `O1_measure/bench/` の5本を対象にする） |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`、`optcc.py` |
| 編集する | `cfg.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が `bench/*.c` のフローグラフを検証して図を書き出す |
| コマ数 | 1 |
| 備考 | 最適化発展シリーズの第2回。この回だけは命令数が減らない（道具を作る回である）。作ったフローグラフを O5・O6・O7 が使う |

この回で作るフローグラフを、以降の回がそのまま使います。

| 回 | 何に使うか |
|----|-----------|
| O5 | 生存変数解析（ブロックの間で情報を伝える） |
| O6 | コピー伝播・死コード除去 |
| O7 | ブロック整列とループ回転（後方辺を探す） |

## 編集するファイル

- `cfg.py`（Step 1: `find_leaders`、Step 2: `build_blocks`、Step 3: `build_edges`）

`Block` クラス・`strip_asm`・`to_dot`（Graphviz 出力）は完成済みです。

## 動かし方

```bash
python3 ../optcc.py --passes '' ../O1_measure/bench/loop_sum.c    # 素の出力を見る
python3 golden.py                                                 # 図を書き出す
```

図は `cfg_out/` に出ます（`dot` があれば PNG も作ります）。

## テスト

```bash
python3 check.py     # リーダ・ブロック・辺の単体テスト(未実装は SKIP)
python3 golden.py    # bench/*.c のフローグラフを検証して図にする
```

土台のコンパイラを差し替えたいときは環境変数 `OPTCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
