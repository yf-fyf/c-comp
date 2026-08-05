# コマ9: ポインタ演算とスケーリング

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/09_pointer_arith/](https://yf-fyf.github.io/c-comp/sessions/09_pointer_arith/) にあります。

## 今日のゴール

コマ8 で入れた型サイズを使って、ポインタ演算・添字 `p[i]`・`sizeof(型名)` を実装する。

## 実装する主な機能

- 添字 `p[i]`（`*(p + i)` の略記）のアドレス計算とスケーリング
- ポインタ演算（`p + 2` が指し先の型サイズ分だけ進む）
- `sizeof(型名)` を翻訳時定数としてコード生成する
- 前置 `++` / `--` を型対応にする（ポインタは 1 要素ぶん進む）
- 多段ポインタ（`int **`）

## 編集するファイル

- `mycc.py`

## テスト

> - `workbook/` から実行する。
> - 前回までのテストが全通していることを前提とする。
> - FAIL したら、まず最初の失敗ケースを単体で確認する。詳しい手順は [`docs/testing.md`](../../docs/testing.md) を参照。

```bash
python3 scaffold/test_runner.py sessions/09_pointer_arith
```
