# 教材更新の移行案内（2026-08-01）

2026-08-01 に教材を広く見直した。その中に、**それより前に取得したファイルと
混ぜると壊れる変更**が含まれている。この文書が、その変更と対処をまとめた唯一の出典である。

## 自分に関係があるか

| 状況 | 対応 |
|------|------|
| 2026-08-01 以降に配布物を取得した | 読まなくてよい |
| それより前に取得したファイルで作業中 | 「まずやること」を読む |
| 発展課題に取り組んでいる／これから始める | あわせて「発展課題の変更」を読む |
| 発展課題の `S3_ptrdiff/` または `L1_struct/` で作業していた | 「発展課題 `S3` と `L1` は中身が入れ替わった」を読む（取得時期を問わず影響する） |
| コマ7 に取り組んでいた／これから取り組む予定だった | 「コマ7 は廃止した」を読む |

手元がどちらか分からないときは、`sessions/06_loops/mycc.py` を開いて
`_continue_stack` と書いてあれば新しい版、`_cont_stack` なら古い版である。

---

## コマ7 は廃止した

**`sessions/07_functions_abi/` は無くなった。** 新しい配布物には入っていない。

コマ7 の主題は「`collect_decls()` を `Block` / `If` / `While` / `For` へ再帰させる」
ことだった。しかし言語仕様は**宣言を書けるのはファイルスコープと関数本体の先頭だけ**と
定めており（[`language_spec.md`](./language_spec.md) の「宣言」節）、
`if` や `while` の中に宣言は現れない。降りていく先に何も無い走査を書く回だったので、
回ごと畳んだ。

仕様改訂後も要る部分は**コマ4 に入れた**。

| コマ7 にあったもの | 行き先 |
|--------------------|--------|
| 関数本体（`Block` ノード）を `collect_decls()` に渡す形 | コマ4。`_reset_func_state()` が `self.collect_decls(node.body)` を呼ぶ |
| `Block` を 1 段開く `collect_decls_Block()` | コマ4。スケルトンに提供済み（実装しなくてよい） |
| `_reset_func_state()` への関数状態初期化の統合 | コマ4〜コマ6 が `super()` で積み上げる形のまま。統合のためだけの回は不要になった |
| `Block` / `If` / `While` / `For` への再帰 | **廃止**。仕様上、そこに宣言は現れない |
| テスト `many_locals.c` / `eight_locals.c` / `minimal.c` | コマ4 の `tests/` へ移した |
| テスト `nested_block.c` / `nested_use.c` / `early_return.c` | コマ5 の `tests/` へ移した（`if` と比較演算を使うため） |

### 手元でどうするか

| 状況 | 対応 |
|------|------|
| コマ7 をまだ始めていない | 何もしなくてよい。コマ6 の次はコマ8 |
| コマ7 に取り組み中・実装済み | 書いた `collect_decls_Block` の中身をコマ4 の `_reset_func_state` 側の呼び出しに読み替える。`collect_decls_If` / `_While` / `_For` は捨ててよい。`sessions/07_functions_abi/` は消す |
| コマ8 以降まで進んでいる | 下の「まずやること」の取り直しに従う。コマ8 の `mycc.py` が読み込む前の回が `07_functions_abi` から `06_loops` に変わっている |

`sessions/07_functions_abi/mycc.py` を残したまま新しいコマ8 を走らせても壊れはしないが、
新しいコマ8 はそれを読まなくなるので、コマ7 に書いた実装は効かなくなる。

**コマ8〜16 の番号・ディレクトリ名・公開 URL は変えていない。** 欠けるのは 07 だけで、
07 は欠番のまま残す（番号の振り直しはしない）。
OCaml 参考実装の `sessions/koma07.ml` も同じ理由で消した。

---

## まずやること — コマ6以降をまとめて取り直す

**1つの回だけ新しいファイルに差し替えてはいけない。**

各回のスケルトンは、`importlib` で前の回の `mycc.py` を読み込んで継承している。
たとえば `sessions/06_loops/mycc.py` の冒頭は `05_if_else/mycc.py` を読み込み、
`Codegen06(prev.Codegen05)` として差分だけを書く形になっている。
コマ8 は コマ6 を、コマ6 は コマ5 を、と数珠つなぎになるので、
**新旧が混ざると、新しい回が古い回に無い名前を呼んで落ちる**。

実際にコマ6 だけ古いまま、コマ8 を新しくして走らせるとこうなる。

```text
AttributeError: 'Codegen08' object has no attribute '_continue_stack'.
Did you mean: '_cont_stack'?
```

そこで、**コマ6 以降のスケルトンをまとめて取り直す**のが安全である。

1. **自分が書いた実装を退避する。** `sessions/` を丸ごとどこかへ複製しておく

   ```bash
   cp -r sessions ../sessions_backup_before_migration
   ```

2. 新しい配布物を取得する（取得方法はいつもどおり）
3. 退避したファイルを見ながら、自分が書いた本体を新しいスケルトンへ移す。
   下の変更一覧にある名前は、移すときに読み替える
4. 進んだところまでのテストを走らせて、元どおり通ることを確かめる

   ```bash
   python3 scaffold/test_runner.py sessions/08_functions_recursion
   ```

コマ16 まで終えて `final/mycc.py` に統合済みなら、`final/mycc.py` も同じ読み替えが要る
（発展課題がそこを土台にする。下の「O4 の前提が変わった」を参照）。

---

## 変更一覧

### 1. `_align_to` → `align_to`（呼び出し側の誤り）

補助関数の定義はもともと `align_to` である（`sessions/04_variables/mycc.py`）。
コマ8・コマ10・コマ12 のスケルトンと発展課題 O4 の `regalloc.py` が、
存在しない `self._align_to(...)` を呼んでいた。呼び出し側を `self.align_to(...)` に直した。

| そのままにすると | 対処 |
|------------------|------|
| 古いスケルトンのままなら、関数を1つコンパイルした時点で `AttributeError: 'Codegen08' object has no attribute '_align_to'. Did you mean: 'align_to'?` が出る | 呼び出しを `self.align_to(...)` に直す |
| 定義側を `_align_to` に改名して回避していた場合、新しいスケルトンでは逆向きの `AttributeError: ... has no attribute 'align_to'` が出る | 定義を `align_to` に戻す。呼び出し側も全部そろえる |

`align_to` は 16 バイト境界のフレームサイズ計算に使う
（[`rv64_reference.md`](./rv64_reference.md)）。

### 2. `_cont_stack` → `_continue_stack`

`continue` の飛び先を積むスタックの名前を、`_break_stack` と対になるようそろえた。
定義は `sessions/06_loops/mycc.py`、参照はコマ8・コマ10 と発展課題 O4 の `regalloc.py` にある。

| そのままにすると | 対処 |
|------------------|------|
| 新旧が混ざると `AttributeError: 'Codegen08' object has no attribute '_continue_stack'. Did you mean: '_cont_stack'?` が出る。コマ8 以降のすべての関数定義で落ちるので、テストは全滅に見える | コマ6 の定義とコマ8・コマ10 の参照を `_continue_stack` にそろえる。自分の `gen_stmt_Continue` の中も同じ |

### 3. 取り直すと復活する TODO（コマ8・コマ10）

コマ8 とコマ10 では、`_reset_func_state` の中にコメントで書かれていた
「パラメータのスロット確保」を `_alloc_params` という別のメソッドに切り出した。
`_emit_func_prologue` の「パラメータをスタックへ退避する」も、
コメントだけだったものが `NotImplementedError` を投げる TODO になっている。

**取り直すと、この2箇所が未実装の TODO として復活する。**
退避した自分のコードから、該当する処理を `_alloc_params` と `_emit_func_prologue` へ移すこと。
移し忘れると `NotImplementedError: _alloc_params を実装してください` で止まる。

---

## 発展課題の変更

### 4. L3 のラッパーが `varcc.py` → `langcc.py`

ラッパー名はファミリごとにそろえる決まりで、L ファミリは `langcc.py` である
（[`../advanced/README.md`](../advanced/README.md) の「ラッパーの名前」）。
L3 だけ `varcc.py` のままだったので改名した。環境変数も `VARCC_*` → `LANGCC_*` になる。

| そのままにすると | 対処 |
|------------------|------|
| `python3 varcc.py ...` は「そのようなファイルはない」で止まる | `python3 langcc.py ...` に読み替える |
| `VARCC_COMPILER` / `VARCC_PASSES` は**エラーにならず黙って無視され**、既定値で走る | `LANGCC_COMPILER` / `LANGCC_PASSES` に書き換える |

### 5. 環境変数の接頭辞

接頭辞は「ラッパーのファイル名から `.py` を取って大文字にしたもの」という規則に統一した。
規則そのものは [`../advanced/README.md`](../advanced/README.md) の「環境変数の名前」にある。

| ラッパー | 旧 | 新 |
|----------|----|----|
| `advanced/optcc.py` | `OPT_COMPILER` / `OPT_PASSES` / `OPT_REGALLOC` / `OPT_ANSWERS` | `OPTCC_COMPILER` / `OPTCC_PASSES` / `OPTCC_REGALLOC` / `OPTCC_ANSWERS` |
| `advanced/B1_fold_peephole/foldcc.py` | `OPTCC_COMPILER` / `OPTCC_PASSES` | `FOLDCC_COMPILER` / `FOLDCC_PASSES` |
| `advanced/L3_variadic/langcc.py` | `VARCC_COMPILER` / `VARCC_PASSES` | `LANGCC_COMPILER` / `LANGCC_PASSES` |

改名前は B1 が `OPTCC_*`、O 系列が `OPT_*` を使っていたため、
**1文字違いの名前が別のラッパーを指す**状態になっていた。

**この項目がいちばん気づきにくい。** 知らない環境変数は読まれないだけで、
**警告も異常終了も出ない**。旧名のまま走らせると、黙って既定値
（土台は `final/mycc.py`、パスは何も適用しない）で通ってしまう。

```bash
# 旧名。パスが1つも適用されないまま終了コード 0 で終わる
OPT_PASSES=isel python3 optcc.py file.c

# 新名。ここで初めて isel が読み込まれる
OPTCC_PASSES=isel python3 optcc.py file.c
```

| 症状 | 疑うところ |
|------|-----------|
| 最適化をかけたはずなのに命令数がまったく減らない | `_PASSES` / `_REGALLOC` が旧名のまま |
| 土台を差し替えたはずなのに「土台のコンパイラが動かない: …/final/mycc.py」で止まる | `_COMPILER` が旧名のまま |

環境変数を1つも設定していないなら、この変更の影響は受けない。

### 6. O4 の前提が変わった

`advanced/O4_regalloc/regalloc.py` は、上の 1 と 2 に追随して
`self.align_to(...)` と `self._continue_stack` を呼ぶようになった。
O4 はコード生成器にパッチを当てる回なので、**土台の `final/mycc.py` 側の名前と一致していないと動かない。**

**古いスケルトンで作った `final/mycc.py` と、新しい O4 の組み合わせは動かない。**
`AttributeError` が `regalloc.py` の中から出る。
先に「まずやること」の取り直しを済ませて、`final/mycc.py` の名前をそろえること。

### 7. B・O 系の命令数の測り方と、資料の数値

**動的命令数の測り方を O1 の方法に統一した。**
[O1 の資料](https://yf-fyf.github.io/c-comp/advanced/O1_measure/)にある
`qemu-riscv64 -one-insn-per-tb -d exec,nochain` で実行を追い、
`nm` で引いた自作関数のアドレス範囲だけに絞る方法である。

以前 B2 の発展課題が挙げていた `qemu-riscv64 -d in_asm` による数え方は**誤った数字を出す**。
qemu が翻訳したブロックを翻訳時に1度だけ表示するものなので、行数を数えても
「実行された回数」にはならない。ループの回数を2倍にしても行数はほとんど変わらないのに、
実際の実行命令数は倍になる。桁は合ってしまうので、間違いに気づきにくい。

**資料の数値も変わった。**

- O1 の資料に「全構成の基準表」（素 / +isel / +regalloc / +copyprop,dce / +layout の
  5構成、静的・動的の両方）を1つだけ置いた。**O 系列の他の回の表は、そこからの差分である**
- O4 の「push/pop が6割近く」は、実測に合わせて「1,183命令のうち 587命令（49.6%）」に直した

`-d in_asm` で数えた値を手元のノートに書いてあるなら、**捨てて測り直すこと**。
自分で測った値と資料の数値が食い違うときは、まず O1 の基準表と突き合わせる。

### 8. 発展課題 `S3` と `L1` は中身が入れ替わった

**`S3_ptrdiff/` と `L1_struct/` は無くなった。** それぞれ `L1_ptrdiff/` と `S3_struct/` になっている。

S ファミリと L ファミリの分かれ目は「その回で作る振る舞いの正解が
`language_spec.md` に書いてあるかどうか」である
（[`../advanced/README.md`](../advanced/README.md) の「S と L の判定基準」）。
この2本だけ判定と ID が食い違っていたので、ID とディレクトリ名を実際に合わせた。
番号は入れ替えで、欠番は作っていない。

| 2026-08-01 より前 | 現在 | ラッパー | 環境変数 |
|-------------------|------|----------|----------|
| `advanced/S3_ptrdiff/` | `advanced/L1_ptrdiff/` | `semcc.py` → `langcc.py` | `SEMCC_*` → `LANGCC_*` |
| `advanced/L1_struct/` | `advanced/S3_struct/` | `langcc.py` → `semcc.py` | `LANGCC_*` → `SEMCC_*` |

公開 URL も同じように変わる。

| 2026-08-01 より前 | 現在 |
|-------------------|------|
| `https://yf-fyf.github.io/c-comp/advanced/S3_ptrdiff/` | `https://yf-fyf.github.io/c-comp/advanced/L1_ptrdiff/` |
| `https://yf-fyf.github.io/c-comp/advanced/L1_struct/` | `https://yf-fyf.github.io/c-comp/advanced/S3_struct/` |

**いちばん危ないのは、番号そのものは両方とも残っていることである。**
`S3` は「ポインタ差」ではなく「構造体の代入」を、
`L1` は「構造体の代入」ではなく「ポインタ差」を指すようになった。
古いブックマークや手元のメモの `S3` / `L1` は、**別の回を指す名前として生き続ける**。

### 手元でどうするか

**書いた `ptrdiff.py` / `structcopy.py` の中身は変わっていない。**
学習者が実装する範囲（Step の切り方、関数名、期待値、テスト）はどれも同じで、
変わったのは置き場所とラッパーの名前だけである。

| 状況 | 対応 |
|------|------|
| どちらもまだ始めていない | 何もしなくてよい。新しい配布物のディレクトリ名で始める |
| `S3_ptrdiff/ptrdiff.py` を書きかけ・実装済み | 書いた `ptrdiff.py` を新しい `advanced/L1_ptrdiff/` へコピーする。`python3 semcc.py ...` は `python3 langcc.py ...` に読み替える |
| `L1_struct/structcopy.py` を書きかけ・実装済み | 書いた `structcopy.py` を新しい `advanced/S3_struct/` へコピーする。`python3 langcc.py ...` は `python3 semcc.py ...` に読み替える |
| `SEMCC_*` / `LANGCC_*` を設定して走らせていた | ラッパーが入れ替わったので接頭辞も入れ替わる。**旧名はエラーにならず黙って無視される**（上の 5 と同じ症状） |

```bash
# 旧: advanced/S3_ptrdiff/ で
python3 semcc.py tests/count.c

# 新: advanced/L1_ptrdiff/ で
python3 langcc.py tests/count.c
```

`test_runner.py` に渡すパスも変わる。

```bash
# workbook/ から
python3 scaffold/test_runner.py --compiler advanced/L1_ptrdiff/langcc.py --tests final/tests
python3 scaffold/test_runner.py --compiler advanced/S3_struct/semcc.py  --tests final/tests
```

他の発展課題（F・B・O・R・Q・P 系列と S1・S2・L2・L3）の ID・ディレクトリ名・
公開 URL は変えていない。

---

## 資料の記述の変更

### 9. コマ11: 実装手順の説明が古かった（配線は最初から提供）

原稿の実装手順3〜5は、文字列収集の走査・`.data` セクション出力・`.text` セクション出力を、
学習者自身が `main()` から呼び出すよう指示する書き方になっていた。
実際のスケルトン（`sessions/11_strings_printf/mycc.py`）では、これらの呼び出しは
最初から `main()` に書かれている（各関数本体に対して `collect_strings_stmt()` を呼ぶループ、
`emit_data_section()` の呼び出し、`.text` セクションの出力）。
資料の説明を、この配線が提供済みであることが分かる書き方に直した。

| そのままだと | 対応 |
|--------------|------|
| 旧い手順の説明を見て、`main()` に自分で走査ループや `.data` 出力の呼び出しを書こうとしていた | 呼び出しはスケルトンにすでにあるので書かなくてよい。呼び出し先のメソッド本体（`NotImplementedError` が出るところ、`_intern()` や `collect_strings_stmt_*` / `collect_strings_expr_*` 各メソッド、`emit_data_section()` 自体、`type_of_expr_Str()`、`codegen_Str()`）を実装する |
| スケルトンのコードと資料の説明が食い違って見えて混乱していた | 訂正後の資料を読み直す。`workbook/sessions/11_strings_printf/mycc.py` 自体は変更していない |

学習者が実装する範囲（TODO の位置）は変わっていない。変わったのは資料の説明だけである。

### 10. テストが 10 本増えた（コマ3・5・9・10・11・13・14）

[`language_spec.md`](./language_spec.md) に「機能→導入コマ→検証テスト」の対応表を作ったとき、
**どのテストからも確かめられていない機能**が見つかった。
そこを埋めるため、7つの回に検証テストを計 10 本足した。

| 回 | 追加したテスト |
|----|----------------|
| コマ3 | `div_round.c` |
| コマ5 | `rel_value.c` |
| コマ9 | `void_func.c` |
| コマ10 | `char_var.c` / `main_argv.c` / `ptr_to_ptr.c` |
| コマ11 | `file_stream.c` / `lib_exit.c` |
| コマ13 | `void_ptr.c` |
| コマ14 | `logical_ops.c` |

そのため、「まずやること」の取り直しをした学習者は、
**すでに終えたはずの回で見覚えのないテストに出会うことがある。**
これは教材が壊れているのでも、前後で食い違っているのでもない。意図して足したテストである。

**とくにコマ14 の `logical_ops.c` に注意すること。**
`&&` / `||` / `!` はもともとコマ14 のスケルトンの実装対象だが、これまで専用のテストが無かった。
取り直した直後にこれが落ちると**「取り直しに失敗した」と読み違えやすい**が、そうではない。
以前から実装対象だったものが、今回から確かめられるようになっただけである。

| 状況 | 対応 |
|------|------|
| 取り直した回で見覚えのないテストが落ちる | 取り直しの失敗を疑う前に、そのテストが上の表にあるか見る。あれば新規追加なので、その機能を自分の実装が満たせているか確かめて直す |
| コマ14 で `logical_ops.c` が落ちる | `&&` / `\|\|` / `!` の実装を見直す。取り直しの手順は関係ない |

追加したテストは、各回の資料のテスト一覧にも載せてある。
