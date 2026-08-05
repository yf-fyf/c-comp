# final

標準トラックの最終成果物を置く。

コマ15で、各 `sessions/NN_xxx/mycc.py` の成果を `final/mycc.py` に統合する。
省略形のテストコマンドは、このディレクトリを対象にする。

## 統合手順

通常回の `mycc.py` は、前の回のクラスを `importlib` で継承した差分だけを書いてきた。
**統合はファイルのコピーではない。** コマ14の `mycc.py` をそのまま `final/mycc.py` へ
置いても、`importlib` が前回ファイルを探す基準パスが変わるため動かない。
この連鎖をたどって全ハンドラを1つのクラスへ展開する必要がある。

1. コマ1からコマ14までの `Codegen` クラスをたどり、全ハンドラ(メソッド)を洗い出す
2. `final/mycc.py` に単一の `Codegen` クラスとして展開する(`importlib` による継承は使わない)
3. `python3 scaffold/test_runner.py` を実行する
4. 落ちたテストを1つずつ切り分ける(対応するコマの小さいテストへ降りて原因を絞る)
5. `final/tests/` が全通したら、コードを読み直して完成チェックを行う

`final/mycc.py` はコマ15開始時点では統合先プレースホルダーである(単体で実行すると
案内メッセージを出して終了する)。完了条件は `final/mycc.py` が単体で起動し、
`final/tests/` が全通することである。

```bash
python3 scaffold/test_runner.py
```

明示的に指定する場合は次のように実行する。

```bash
python3 scaffold/test_runner.py --compiler final/mycc.py --tests final/tests
```

## final/tests

`final/tests/` はコマ1からコマ15までの機能をまとめて確認する参考テストである。
このテストセットの全通を標準トラック完成の目安とする。

## このあと

`final/tests/` が全通すれば**実装は完成**である。**学習経路の完了はコマ16(発表会)**で、
完成した `final/mycc.py` を説明できる形に整えて発表する。発表を待たずに、選択制の
発展課題([`../advanced/README.md`](../advanced/README.md))へ進んでもよい。
発展課題に進まず、Python 版の補修・仕上げに時間を使うのも同じだけ正当な選択である。
詳細は [`../docs/getting_started.md`](../docs/getting_started.md) の「コマ15 のあと」を参照。
