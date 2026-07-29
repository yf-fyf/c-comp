# final

標準トラックの最終成果物を置く。

コマ16で、各 `sessions/NN_xxx/mycc.py` の成果を `final/mycc.py` に統合する。
省略形のテストコマンドは、このディレクトリを対象にする。

## 統合手順

1. 第15回までに完成した `mycc.py` を `final/mycc.py` に反映する
2. `python3 scaffold/test_runner.py` を実行する
3. 落ちたテストを1つずつ切り分ける
4. `final/tests/` が全通したら、コードを読み直して完成チェックを行う

`final/mycc.py` はコマ16開始時点では統合先プレースホルダーである。
学生は自分の実装をここへ移す。

```bash
python3 scaffold/test_runner.py
```

明示的に指定する場合は次のように実行する。

```bash
python3 scaffold/test_runner.py --compiler final/mycc.py --tests final/tests
```

## final/tests

`final/tests/` は第1回から第15回までの機能をまとめて確認する参考テストである。
このテストセットの全通を標準トラック完成の目安とする。
