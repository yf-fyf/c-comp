# S2: `int` は32ビット — 桁あふれを正しく折り返す

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/S2_int32/](https://yf-fyf.github.io/c-comp/advanced/S2_int32/) にあります。

## 今日のゴール

`int` の演算を32bit命令（`addw` など）で行い、桁あふれが C のとおりに折り返すようにする。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ13（`malloc`）まで。折り返しの考え方そのものは型サイズまでで足りるが、安全網の `tests/pointer_ok.c` が `struct` と `malloc` を使う。完了条件のうち `golden.py` は完成した `final/mycc.py` を土台に `fixed17` を回すので、やり切るにはコマ16 も要る |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`、ラッパー `semcc.py`（配布済み・完成品） |
| 編集する | `narrow.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が折り返しのテストの通過と `fixed17` 全通を報告する |
| コマ数 | 1 |
| 仕様との関係 | **仕様の内側**。`language_spec.md` は `int` を「4 バイト符号付き整数（32 ビット 2 の補数）」と定めているのに、実装は演算を 64bit 命令で行っている。実装を仕様へ合わせる |
| 備考 | 意味論発展シリーズの第2回。S1・S3 とは独立している。3本の中では最も気づきにくいずれである |

## 編集するファイル

- `narrow.py`（Step 1: narrow）

## テスト

```bash
python3 check.py     # narrow の入出力を直接確認(未実装は SKIP)
python3 golden.py    # 折り返しのテスト + fixed17
```

`tests/pointer_ok.c` は「直しすぎ（アドレス計算まで32bit化）」を検出するための安全網です。

土台のコンパイラを差し替えたいときは環境変数 `SEMCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
