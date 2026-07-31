# L2: 複合代入 — 左辺を1回しか評価しない

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/L2_compound_assign/](https://yf-fyf.github.io/c-comp/advanced/L2_compound_assign/) にあります。

## 今日のゴール

`x += 3;` `p -= 1;` `x %= 5;` のような複合代入（`+= -= *= /= %=`）を、
字句・構文・コード生成の3段すべてで動くようにする。

複合代入は `language_spec.md` の外側にある機能です。この回で追加する構文と意味論は
資料の「L2 が追加する仕様」節が定義します。

`x = x + 3` への書き換え（脱糖）では駄目で、`*bump() += 10` のように
左辺が副作用を持つと `bump()` が2回呼ばれてしまいます。
「複合代入の左辺は1回だけ評価される」がこの回の中心的な規則です。

前提はコマ14 まで。**`mycc.py` も `scaffold/lexer.py` も `scaffold/parser.py` も
書き換えません**（`langcc.py` が字句・構文・コード生成に差し込みます）。

## 編集するファイル

- `compound.py`（Step 1: extend_puncts、Step 2: gen_compound_assign、Step 3: scale_rhs_for_ptr）

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # 複合代入のテスト + fixed17
```

`tests/*.c` は標準トラックの字句では読めないソースなので、
web の golden テストでは skip として数えられます（失敗ではありません）。
