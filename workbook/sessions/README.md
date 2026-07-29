# sessions

各コマの作業内容を置く。
学生は、その日の `sessions/NN_xxx/` だけを見ればよい。

各セッションは次の形に揃える。

```text
sessions/NN_xxx/
├── handout.pdf   # 講義資料（まず読む）
├── README.md     # 作業指示・テストコマンド（簡易）
├── mycc.py       # 編集するコンパイラ
└── tests/
```

各回の完成形に相当する OCaml 版参考実装は [`../ocaml/`](../ocaml/README.md) にまとめて置いてある。

テストはセッションディレクトリを渡して実行する。

```bash
python3 scaffold/test_runner.py sessions/06_loops
```
