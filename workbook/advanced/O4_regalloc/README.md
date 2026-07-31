# O4: レジスタ割り当て（2コマ）

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/O4_regalloc/](https://yf-fyf.github.io/c-comp/advanced/O4_regalloc/) にあります。

## 今日のゴール

局所変数をメモリではなく **callee-saved レジスタ（s1〜s11）** に置く。
変数への代入が5命令から1命令になる。このシリーズでいちばん効果が大きい回です。

## 前提

| 種別 | 内容 |
|------|------|
| **必須** | コマ16（完成した `final/mycc.py`） |
| **必須** | O1（`measure.py`）—— `golden.py` が効果の測定に使う |
| 推奨 | O3（命令選択）—— 効果を isel をかけた状態と比べるため |

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
