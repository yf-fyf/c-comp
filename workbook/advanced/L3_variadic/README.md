# L3: 可変長引数の定義 — `printf` の側に立つ

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/L3_variadic/](https://yf-fyf.github.io/c-comp/advanced/L3_variadic/) にあります。

## 今日のゴール

`int sum(int n, ...)` のような可変長引数の関数を自分で定義できるようにする。
引数レジスタ a0〜a7 をフレームに退避し、`__arg(i)` で添字読み出しできるようにする。

言語仕様は「可変長引数関数の定義」を**非対応と決めて外しています**
（表の欄は「外部プロトタイプのみ許可」）。いまのコンパイラに書くと
`構文解析エラー: 可変長 '...' はプロトタイプ宣言でのみ使えます` で止まります。
この回は、その**仕様が意図的に落とした機能を自分で足す**回です。

前提はコマ11 まで。**`mycc.py` も `scaffold/parser.py` も書き換えません**
（`varcc.py` が構文とコード生成の両方に差し込みます。
定義側の `...` を受理する parser shim もそちらの担当です）。

## 編集するファイル

- `variadic.py`（Step 1: reserve_save_area、Step 2: gen_save_registers、
  Step 3: is_arg_builtin / gen_arg_access）

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # 可変長関数のテスト + fixed17
```
