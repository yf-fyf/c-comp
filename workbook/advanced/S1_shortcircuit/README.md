# S1: 短絡評価 — `&&` と `||` の本当の意味

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/S1_shortcircuit/](https://yf-fyf.github.io/c-comp/advanced/S1_shortcircuit/) にあります。

## 今日のゴール

`&&` / `||` を C の規格どおり「必要なときだけ右辺を評価する」形に直す。
`if (p != 0 && p->val > 0)` が書けるようになる。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ12（構造体）まで。短絡の考え方そのものは関数呼び出しまでで足りるが、`tests/null_guard.c` が `struct` を使う（短絡が要る代表例の `p != 0 && p->val > 0` がポインタとフィールド参照そのものなので避けられない）。完了条件のうち `golden.py` は完成した `final/mycc.py` を土台に `fixed17` を回すので、やり切るにはコマ16 も要る |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`、ラッパー `semcc.py`（配布済み・完成品） |
| 編集する | `shortcircuit.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が短絡の要るテストの通過と `fixed17` 全通を報告する |
| コマ数 | 1 |
| 仕様との関係 | **仕様の内側**。`language_spec.md` は `&&` / `||` を「短絡しない」と定めており、実装はそのとおりに動いている。この回はずれを仕様の側で直す — 仕様が例外 E3 として自ら明記している ISO C との差を、C の側へ寄せる |
| 備考 | 意味論発展シリーズの第1回。仕様が本物の C とわざと違えている点（例外 E3）を C の側へ寄せる回 |

## 編集するファイル

- `shortcircuit.py`（Step 1: gen_and、Step 2: gen_or）

## テスト

```bash
python3 check.py     # 生成された命令列の構造を確認(未実装は SKIP)
python3 golden.py    # 短絡が要るテスト + fixed17
```

土台のコンパイラを差し替えたいときは環境変数 `SEMCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
