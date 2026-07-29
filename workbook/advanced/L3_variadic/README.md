# L3: 可変長引数の定義 — `printf` の側に立つ

この回の資料は `handout.pdf` を参照してください。

## 今日のゴール

`int sum(int n, ...)` のような可変長引数の関数を自分で定義できるようにする。
引数レジスタ a0〜a7 をフレームに退避し、`__arg(i)` で添字読み出しできるようにする。

前提はコマ11 まで。**`mycc.py` も `scaffold/parser.py` も書き換えません**
（`varcc.py` がパーサとコード生成の両方に差し込みます）。

## 編集するファイル

- `variadic.py`（Step 1: reserve_save_area、Step 2: gen_save_registers、
  Step 3: is_arg_builtin / gen_arg_access）

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # 可変長関数のテスト + fixed15
```
