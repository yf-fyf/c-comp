# O4: レジスタ割り当て（2コマ）

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/O4_regalloc/](https://yf-fyf.github.io/c-comp/advanced/O4_regalloc/) にあります。

## 今日のゴール

局所変数をメモリではなく **callee-saved レジスタ（s1〜s11）** に置く。
変数への代入が5命令から1命令になる。このシリーズでいちばん効果が大きい回です。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ16（完成した `final/mycc.py`）、O1（測定基盤。`golden.py` が `measure.py` と `O1_measure/bench/` を使う） |
| 推奨の前提 | O3（命令選択）。実質必須に近い。資料の測定値は O1 の全構成の基準表の `+isel` 列を基準にしているので、O3 が無いと表と突き合わせられない |
| 改変しない | `mycc.py`、`scaffold/`、`optcc.py` |
| 編集する | `regalloc.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が `fixed17` 全通と静的・動的の命令数削減を報告する |
| コマ数 | 2 |
| 備考 | 最適化発展シリーズの第4回。このシリーズでいちばん効果が大きい。アセンブリのパスではなく、コード生成器へのパッチである。コマ1は Step 1〜4、コマ2は Step 5〜6 |

**`mycc.py` は書き換えません**。パッチを外から当てます。

## 2コマの区切り

| コマ | やること | 到達点 |
|------|----------|--------|
| 1 | Step 1〜4。`worth_promoting` は `return list(names)` のまま | `golden.py` が通り、`fib_rec` **だけ**遅くなることが測れる |
| 2 | Step 5〜6 | `fib_rec` の悪化が消える |

コマ1の終わりで区切っても、`check.py` の Step 1〜4 と `golden.py` は通ります。
コマ2はそこから再開できます。

## 編集するファイル

- `regalloc.py`

これまでの回と違い、**アセンブリのパスではなくコード生成器へのパッチ**です。
「どの変数の `&` が取られているか」は AST を見ないと分からないので、
アセンブリになってからでは判断できません。

## 動かし方

```bash
python3 ../optcc.py --regalloc --passes isel ../O1_measure/bench/loop_sum.c
python3 ../optcc.py            --passes isel ../O1_measure/bench/loop_sum.c  # 割り当てなし
```

## テスト

```bash
python3 check.py     # 各関数の単体テスト(未実装は SKIP)
python3 golden.py    # fixed17 + ベンチマーク + 静的/動的の削減
```

`golden.py` は**先に fixed17 を確認**します。この回はいちばん意味を壊しやすいためです。

土台のコンパイラを差し替えたいときは環境変数 `OPTCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
