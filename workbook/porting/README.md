# C 移植・セルフホスト

Python 版コンパイラを参照実装として、C 版コンパイラへ移植するトラック。
発展課題（[`../advanced/`](../advanced/README.md)）が1回で完結するトピック群なのに対し、
こちらは複数回に渡って積み上げる長期トラックである。

前提: コマ16 の完成した `../final/mycc.py`。

---

## 基本方針

Python 版コンパイラのアルゴリズムを**再発明せず**、データ構造を C に写す。
移植は「アルゴリズムの再発明」ではなく「データ構造の C 化」である。

| Python | C |
|--------|---|
| class / dataclass | `struct` |
| `dict` | 連結リスト（線形探索） |
| `list.append` | 末尾連結 |
| `None` | `NULL` |
| `isinstance(node, AddNode)` | `node->kind == ND_ADD` |
| `f"  li a0, {val}\n"` | `printf("  li a0, %d\n", val)` |

## C 実装の規約

- **言語**: Core プロファイル自身で書く（セルフホスト可能な範囲に収める）
- **命名規則**: 型 `snake_case` / 関数 `snake_case` / 定数 `UPPER_SNAKE`
- **メモリ管理**: `malloc` のみ使用。`free` は不要（コンパイラはプロセス終了時に一括解放）
- **エラー処理**: `fprintf(stderr, ...)` + `exit(1)` で即終了
- **コメント**: `//` 一行コメントのみ

RV64 の呼び出し規約とアラインメント規則は [`../docs/rv64_reference.md`](../docs/rv64_reference.md) を参照。

## 想定構成

```text
porting/
├── README.md            # このファイル
├── code_example.md      # コマ17〜24 の到達目標コード例
├── Makefile             # 自分で用意する
├── src/                 # ここに C 版を書く
│   ├── main.c
│   ├── lexer.c / lexer.h
│   ├── parser.c / parser.h
│   ├── codegen.c / codegen.h
│   └── type.c / type.h
├── tests/               # 前処理の自前実装を検証するテスト
└── verify_selfhost.sh   # ブートストラップ検証スクリプト（雛形）
```

## 進め方

1. **インフラ移植**: `struct Node`・`struct Type`・シンボルテーブル・`emit()`
2. **コード生成移植①**: 算術・変数・制御構文
3. **コード生成移植②**: 関数・ポインタ
4. **コード生成移植③**: 配列・構造体・グローバル変数
5. **フロントエンド**: `scaffold/lexer.py` / `parser.py` を読解して移植、または自作
6. **セルフホスト挑戦**: 不足機能を実装し、自分自身をコンパイルする

最初の目標は、算術式・変数・制御構文までを C 版で出力できるようにすること。
各段階でどこまでコンパイルできればよいかは [`code_example.md`](./code_example.md) に示してある。

## ビルド

`Makefile` は自分で用意する。最小構成の例:

```bash
gcc -O0 -g -static -o mycc src/*.c
./mycc test.c > out.s
riscv64-linux-gnu-gcc -static out.s -o out
qemu-riscv64 ./out; echo $?
```

## テスト

```bash
# fixed15 を C 版で通す
python3 ../scaffold/test_runner.py --compiler ./mycc --tests ../final/tests

# 前処理の自前実装（#include / #define）を検証する
python3 ../scaffold/test_runner.py --compiler ./mycc --tests tests
```

## セルフホストの検証

`verify_selfhost.sh` は雛形である。以下を段階的に確認する。

```bash
gcc -o mycc_stage0 src/*.c                       # Stage 0: gcc でビルド
./mycc_stage0 src/*.c -o mycc_stage1             # Stage 1: 自分でビルド
python3 ../scaffold/test_runner.py --compiler ./mycc_stage1 --tests ../final/tests
python3 ../scaffold/test_runner.py --compiler ./mycc_stage1 --tests tests
```

参考達成条件: `mycc_stage1` の生成成功 + `fixed15` 全通 + `tests/` の2本通過。
セルフホストは必達目標ではなく、自主課題として扱う。
