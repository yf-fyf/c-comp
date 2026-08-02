# sessions

各コマの作業内容を置く。
学習者は、その日の `sessions/NN_xxx/` だけを見ればよい。

講義資料は <https://yf-fyf.github.io/c-comp/sessions/> にある。まずこれを読む。

各セッションは次の形に揃える。

```text
sessions/NN_xxx/
├── README.md     # 資料へのリンク・作業指示・テストコマンド
├── mycc.py       # 編集するコンパイラ
└── tests/
```

各回の完成形に相当する OCaml 版参考実装は [`../ocaml/`](../ocaml/README.md) にまとめて置いてある。

テストはセッションディレクトリを渡して実行する。

```bash
python3 scaffold/test_runner.py sessions/06_loops
```
