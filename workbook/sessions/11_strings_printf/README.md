# コマ11: 文字列リテラル + printf

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/11_strings_printf/](https://yf-fyf.github.io/c-comp/sessions/11_strings_printf/) にあります。

## 今日のゴール

文字列リテラルを `.data` セクションに出力し、`printf` 呼び出しを動かす。

## 実装する主な機能

- 文字列リテラルを `.data` セクションに配置し、ラベルを割り当てる
- 文字列リテラルのアドレスを `char *` として扱う
- `printf` など外部関数の呼び出しをコード生成する（`printf` 自体は実装せず libc のものを使う）

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/11_strings_printf
```
