# コマ11b: 式の走査と libc 活用

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/11b_expr_walk_libc/](https://yf-fyf.github.io/c-comp/sessions/11b_expr_walk_libc/) にあります。

## 今日のゴール

コマ11a で文に対して書いた走査を式へ広げ、どこに置かれた文字列リテラルでも
`.data` に出るようにする。そのうえで `lib.h` の残りの関数を使ってみる。

新しい概念はほとんど無い。コマ11a と同じ形のハンドラを、式の種類の数だけ書く回である。

## 実装する主な機能

- 二項演算・単項演算・添字・三項演算子の中にある文字列リテラルを集める
- `lib.h` のストリーム関数（`fdopen` / `fprintf` / `fopen` / `fread` / `fclose`）と `exit` を使う

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/11b_expr_walk_libc
```
