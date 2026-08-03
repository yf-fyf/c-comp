# コマ2: 算術式コード生成

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/02_arithmetic_codegen/](https://yf-fyf.github.io/c-comp/sessions/02_arithmetic_codegen/) にあります。

## 今日のゴール

整数リテラルと算術演算を RV64 アセンブリに変換する。`codegen(node)` は、`node` が表す式を計算し、その結果が実行時に `a0` レジスタに入るようなアセンブリを出力する。

## 実装する主な機能

- 整数リテラル・単項マイナスをコード生成する
- 四則演算（`+` `-` `*` `/`）と剰余 `%` をコード生成する
- カッコで囲まれた式を正しい優先順位で評価する
- 計算結果を `a0` レジスタに残す `codegen(node)` を実装する

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/02_arithmetic_codegen
```
