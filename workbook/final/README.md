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
2. `final/mycc.py` に単一の `Codegen` クラスとして展開する(`importlib` による継承は使わない)。型表・char変換・条件式の共通型・大域の整列補助も引き継ぐ
3. `python3 scaffold/test_runner.py` を実行する
4. 落ちたテストを1つずつ切り分ける(対応するコマの小さいテストへ降りて原因を絞る)
5. `final/mycc.py` でコマ2〜14の全テストも通し、コードを読み直して完成チェックを行う

`final/mycc.py` はコマ15開始時点では統合先プレースホルダーである(単体で実行すると
案内メッセージを出して終了する)。完了条件は `final/mycc.py` が単体で起動し、
`final/tests/` とコマ2〜14の全テストがこの最終コンパイラで通ることである。

```bash
python3 scaffold/test_runner.py
```

明示的に指定する場合は次のように実行する。

```bash
python3 scaffold/test_runner.py --compiler final/mycc.py --tests final/tests
```

過去回のテストも、同じ `final/mycc.py` で確認する。

```bash
for tests in sessions/0[2-9]_*/tests sessions/1[0-4]_*/tests; do
  python3 scaffold/test_runner.py --compiler final/mycc.py --tests "$tests" || exit 1
done
```

文字列収集の二項走査には`And`・`Or`も含める。`logic_string_and.c` / `logic_string_or.c`と、
子の関数呼出しに文字列がある`logic_string_call_and.c` / `logic_string_call_or.c`を最終版でも確認する。

全回 `FAIL: 0` を確認する。コマ14の補助ソースの `SKIP` は正常である。
詳しくは [`../docs/testing.md`](../docs/testing.md#最終コンパイラで過去回の全テストを確認する)を参照。

## final/tests

`final/tests/` は主要な機能を組み合わせて確認する17本の総合テストである。
論理演算・`char`・複数ファイル・ストリーム操作は過去回のテストで確認する。

## このあと

上の総合テストと過去回の全テストが通れば**実装は完成**である。
不正入力の診断については [`../docs/language_spec.md`](../docs/language_spec.md#diagnostics)に保証範囲を示す。
**学習経路の完了はコマ16(発表会)**で、
完成した `final/mycc.py` を説明できる形に整えて発表する。発表を待たずに、選択制の
発展課題([`../advanced/README.md`](../advanced/README.md))へ進んでもよい。
発展課題に進まず、Python 版の補修・仕上げに時間を使うのも同じだけ正当な選択である。
詳細は [`../docs/getting_started.md`](../docs/getting_started.md) の「コマ15 のあと」を参照。
