# O5: 生存変数解析

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/O5_liveness/](https://yf-fyf.github.io/c-comp/advanced/O5_liveness/) にあります。

## 今日のゴール

「この地点から先で、このレジスタの値がまだ読まれるか」を、
フローグラフ全体にわたって求める。**後ろ向き**のデータフロー解析を1つ作る。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | O1（`golden.py` が `O1_measure/bench/` の5本を対象にする）、O2（フローグラフの上で解く）、O4（割り当て前は解析しても何も出てこない） |
| 推奨の前提 | O3（命令選択） |
| 改変しない | `mycc.py`、`scaffold/`、`optcc.py` |
| 編集する | `liveness.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が `bench/*.c` で「割り当て前は空振り、割り当て後に効く」ことを確認する |
| コマ数 | 1 |
| 備考 | 最適化発展シリーズの第5回。この回は命令数を減らさない（解析そのものが成果物で、O6 が使う） |

**この回は命令数を減らしません。** 解析そのものが成果物で、
O6（コピー伝播と死コード除去）がこれを使います。

## 編集するファイル

- `liveness.py`（Step 1: `def_use`、Step 2: `block_def_use` / `solve`、
  Step 3: `live_after`、Step 4: `live_across_calls`）

呼び出し規約の定数、`_is_reg` / `_base_of`、`restored_saved`、
可視化の `annotate` は完成済みです。

`ret` が読む callee-saved は**関数ごとに違います**。O4 のエピローグは
昇格した変数の分だけ `ld sN, ...(s0)` を出すので、それを集めた
`restored_saved(blocks)` の値を `def_use(insn, saved)` に渡します。
`s1`〜`s11` を無条件に読むことにすると、触ってもいないレジスタが
全ブロックで「生きている」ことになり、測定が意味を失います。

## 動かし方

```bash
python3 golden.py                       # 割り当ての前後で解析結果を比べる
```

図は `cfg_out/` に出ます。各ブロックに `in:` / `out:` が注記されます。

## テスト

```bash
python3 check.py     # def_use と方程式の解の単体テスト(未実装は SKIP)
python3 golden.py    # bench/*.c で「割り当て前は空振り、割り当て後に効く」を確認
```

`check.py` の Step 2 には**ループを含む例**が入っています。
1回なめただけでは解けず、収束するまで繰り返す必要があることを確かめます。

土台のコンパイラを差し替えたいときは環境変数 `OPTCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
