# デバッグ手順

動かないときは、複雑な入力をそのまま追わず、**小さい入力に戻す**。

---

## 基本手順

1. 失敗したテストを単体で確認する
2. 生成アセンブリをファイルに保存して読む
3. qemu の終了コードを確認する
4. 関数呼び出しで壊れる場合は `ra`、`s0`、スタックアラインメントを見る
5. ポインタで壊れる場合は `codegen()` と `codegen_lval()` の区別を見る

```bash
python3 sessions/03_arithmetic_codegen/mycc.py sessions/03_arithmetic_codegen/tests/add.c > out.s
riscv64-linux-gnu-gcc -x assembler -static out.s -o out
qemu-riscv64 ./out; echo $?
```

テストの走らせ方は [`testing.md`](./testing.md) を参照。

## 症状から当たりをつける

| 症状 | よくある原因 | 見るところ |
|------|-------------|-----------|
| `FAIL: compile — NotImplementedError: …` | その回の TODO が残っている | メッセージが指す関数を実装する。全文が要るなら `python3 sessions/NN_xxx/mycc.py <入力.c>` を直接実行する |
| `FAIL: assemble — …` | 出力したアセンブリが構文として通らない | 生成結果をファイルに保存して該当行を見る（`python3 … > out.s`） |
| `Illegal instruction` / `Bus error` | スタックアラインメント違反（16バイト境界） | `align_to(n, 16)` を通しているか。`call` 直前の `sp` も対象で、そのとき積んでいる一時値が奇数個ならずれている（[`rv64_reference.md`](./rv64_reference.md)） |
| 終了コードが 0 になる | `return` の値が `a0` に残っていない | 最後の `codegen()` のあとで `a0` を上書きしていないか |
| 期待値と 256 ずれる | 終了コードは 0〜255 | テスト側の期待値を見直す |
| 関数から戻ると壊れる | `ra` / `s0` の退避漏れ、フレームサイズの計算違い | プロローグとエピローグが対称か |
| 再帰の途中で壊れる | 引数の退避漏れ（`a0`–`a7` は caller-saved） | 再帰呼び出しの前後で引数を保存しているか |
| ポインタ経由の代入が効かない | `codegen()` と `codegen_lval()` の混同 | `*p = v;` の左辺は `codegen_lval()` |
| 配列の添字がずれる | ポインタ演算で要素サイズを掛けていない | `size_of_ty_str()` / `elem_ty_str()` を通しているか |
| 未定義変数で黙って動く | シンボルテーブルの探索順序 | `_locals` → `_globals` の順に引いているか |
| `AttributeError: … has no attribute '_continue_stack'` / `'_align_to'` / `'align_to'` | 2026-08-01 より前に取得したファイルと後のファイルが混ざっている | [`migration.md`](./migration.md)。回ごとのスケルトンは前の回を継承するので、一部だけ差し替えると壊れる |
| 最適化をかけたのに命令数が変わらない（発展課題） | 環境変数が旧名のままで黙って無視されている | [`migration.md`](./migration.md) の「環境変数の接頭辞」 |

## アセンブリを読むときの順序

1. `.globl` とラベルが期待どおり出ているか
2. プロローグでフレームサイズが正しいか
3. 問題の式だけを追う（値が `a0` に残るか、アドレスが `a0` に残るか）
4. エピローグがプロローグと対称か

## gdb でステップ実行する

終了コードだけでは原因が分からないときに使う。

```bash
# qemu をデバッグサーバとして起動
qemu-riscv64 -g 1234 ./out

# 別のターミナルで gdb を繋ぐ
gdb-multiarch ./out
(gdb) target remote :1234
(gdb) break main
(gdb) stepi
(gdb) info registers a0 sp s0 ra
```

`Illegal instruction` の発生箇所を特定するときは、止まった時点の `sp` が
16 の倍数になっているかを確認する。
