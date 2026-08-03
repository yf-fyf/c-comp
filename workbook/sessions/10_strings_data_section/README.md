# コマ10: 文字列リテラルと .data セクション

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/10_strings_data_section/](https://yf-fyf.github.io/c-comp/sessions/10_strings_data_section/) にあります。

## 今日のゴール

文字列リテラルを `.data` セクションに出力し、`printf` 呼び出しを動かす。

## 実装する主な機能

- 文字列リテラルにラベルを割り当て、`.data` セクションへ `.byte` 列として出力する
- 文（`if` / `while` / `for` など）を再帰的にたどって文字列リテラルを集める
- 文字列リテラルのアドレスを `char *` として扱う
- `printf` など外部関数の呼び出しをコード生成する（`printf` 自体は実装せず libc のものを使う）

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/10_strings_data_section
```
