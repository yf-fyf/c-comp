# L2: 初期化子リスト — 宣言と同時に値を入れる

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/L2_initializer/](https://yf-fyf.github.io/c-comp/advanced/L2_initializer/) にあります。

## 今日のゴール

`int a[3] = {1,2,3};` と `char s[6] = "hello";` を、
ローカル・グローバルの両方で書けるようにする。

前提はコマ14 まで。**`mycc.py` も `scaffold/parser.py` も書き換えません**
（`langcc.py` がパーサとコード生成の両方に差し込みます）。

## 編集するファイル

- `initializer.py`（Step 1: init_values、Step 2: gen_local_init、Step 3: global_init_data）

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # 初期化子のテスト + fixed15
```
