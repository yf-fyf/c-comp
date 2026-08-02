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

分量をならすため、コマ10 は `10a_types/` と `10b_pointer_arith/` に、
コマ11 は `11a_strings_data_section/` と `11b_expr_walk_libc/` に分かれている。
コマ12 とコマ13 は `12plus13_struct_malloc_list/` の1回にまとめてある。
分割前の `10_types_pointers/`・`11_strings_printf/`・`12_struct/`・`13_sizeof_malloc_list/` も
そのまま置いてあるので、進行中の手元の作業は移し替えなくてよい。

各回の完成形に相当する OCaml 版参考実装は [`../ocaml/`](../ocaml/README.md) にまとめて置いてある。

テストはセッションディレクトリを渡して実行する。

```bash
python3 scaffold/test_runner.py sessions/06_loops
```
