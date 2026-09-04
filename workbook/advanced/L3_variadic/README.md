# L3: 可変長引数の定義 — `printf` の側に立つ

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/L3_variadic/](https://yf-fyf.github.io/c-comp/advanced/L3_variadic/) にあります。

## 今日のゴール

`int sum(int n, ...)` のような可変長引数の関数を自分で定義できるようにします。
引数レジスタ a0〜a7 をフレームに退避し、`__arg(i)` で添字読み出しできるようにします。

言語仕様は「可変長引数関数の定義」を**非対応と決めて外しています**
（表の欄は「外部プロトタイプのみ許可」）。いまのコンパイラに書くと
`構文解析エラー: 可変長 '...' はプロトタイプ宣言でのみ使えます` で止まります。
この回は、その**仕様が意図的に落とした機能を自分で足す**回です。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ10（`printf` の呼び出し）まで。完了条件のうち `golden.py` は完成した `final/mycc.py` を土台に `fixed17` を回すので、やり切るにはコマ15 も要る |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`（`parser.py` を含む）、ラッパー `langcc.py`（配布済み・完成品） |
| 編集する | `variadic.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が可変長関数のテストの通過と `fixed17` 全通を報告する |
| コマ数 | 1 |
| 仕様との関係 | **仕様の外側**。`language_spec.md` は可変長引数関数の定義を「外部プロトタイプのみ許可」として外しており、定義を書くと構文解析エラーになる。呼び出し規約に合わせた意味をこの回で決めて足す |
| 備考 | 言語機能発展シリーズ。R2（自前 `printf`）が `printf1(fmt, iarg, sarg)` という不格好な形を強いられた、その理由を解消する回でもある |

定義側の `...` を受理する parser shim も `langcc.py` の担当です。

## 編集するファイル

- `variadic.py`（Step 1: reserve_save_area、Step 2: gen_save_registers、
  Step 3: is_arg_builtin / gen_arg_access）

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # 可変長関数のテスト + fixed17
```

土台のコンパイラを差し替えたいときは環境変数 `LANGCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
