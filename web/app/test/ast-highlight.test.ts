// @vitest-environment jsdom
import { EditorState } from "@codemirror/state";
import { describe, expect, it } from "vitest";
import { createRequire } from "node:module";
import {
  hoverRangeField,
  outerRange,
  selectedRangeField,
  setHoverRanges,
  setSelectedRanges,
  spanForLine,
  spansForRanges,
  stmtForLine,
  stmtsForRanges,
} from "../src/ast-highlight";
import type {
  AstNode,
  CompileResult,
  ParseResult,
  SourceRange,
  SpanEntry,
  StmtSpan,
} from "../src/types";

function ranges(state: EditorState, field: typeof hoverRangeField): [number, number][] {
  const result: [number, number][] = [];
  state.field(field).between(0, state.doc.length, (from, to) => {
    result.push([from, to]);
  });
  return result;
}

describe("AST source decorations", () => {
  it("指定された文字範囲だけを装飾する", () => {
    let state = EditorState.create({
      doc: "return 1 + 2;",
      extensions: [hoverRangeField, selectedRangeField],
    });
    state = state.update({ effects: setHoverRanges.of([{ from: 7, to: 12 }]) }).state;
    expect(ranges(state, hoverRangeField)).toEqual([[7, 12]]);
  });

  it("hover解除と固定選択を独立して扱う", () => {
    let state = EditorState.create({
      doc: "return 1 + 2;",
      extensions: [hoverRangeField, selectedRangeField],
    });
    state = state.update({
      effects: [
        setHoverRanges.of([{ from: 7, to: 8 }]),
        setSelectedRanges.of([{ from: 11, to: 12 }]),
      ],
    }).state;
    state = state.update({ effects: setHoverRanges.of([]) }).state;
    expect(ranges(state, hoverRangeField)).toEqual([]);
    expect(ranges(state, selectedRangeField)).toEqual([[11, 12]]);
  });

  it("編集時に古いAST範囲を破棄する", () => {
    let state = EditorState.create({
      doc: "1 + 2",
      extensions: [hoverRangeField, selectedRangeField],
    });
    state = state.update({ effects: setSelectedRanges.of([{ from: 0, to: 5 }]) }).state;
    state = state.update({ changes: { from: 0, insert: "0 + " } }).state;
    expect(ranges(state, selectedRangeField)).toEqual([]);
  });
});

// int main() { x = 3; if (x) { return 1; } } を模した対応表（数値は位置と行の関係だけが要点）
const ASSIGN: StmtSpan = { sourceRanges: [{ from: 10, to: 16 }], fromLine: 5, toLine: 9 };
const RETURN: StmtSpan = { sourceRanges: [{ from: 30, to: 39 }], fromLine: 14, toLine: 16 };
const BLOCK: StmtSpan = { sourceRanges: [{ from: 28, to: 41 }], fromLine: 14, toLine: 16 };
const IF: StmtSpan = { sourceRanges: [{ from: 18, to: 41 }], fromLine: 10, toLine: 17 };
const MAP = [ASSIGN, RETURN, BLOCK, IF];

describe("AST ノード ↔ 命令の対応（文単位）", () => {
  it("文そのものを選ぶとその文の命令になる", () => {
    expect(stmtsForRanges(MAP, [{ from: 10, to: 16 }])).toEqual([ASSIGN]);
  });

  it("文より小さいノードは、それを含む最も内側の文に落ちる", () => {
    // 代入の右辺だけを選んでも、代入文の命令が対応する
    expect(stmtsForRanges(MAP, [{ from: 14, to: 15 }])).toEqual([ASSIGN]);
    // return の中の式は、if でも block でもなく return 文に落ちる
    expect(stmtsForRanges(MAP, [{ from: 37, to: 38 }])).toEqual([RETURN]);
  });

  it("文を含むノードは、含まれる文をすべて集める", () => {
    expect(stmtsForRanges(MAP, [{ from: 0, to: 50 }])).toEqual(MAP);
  });

  it("範囲を持たないノード（マクロ展開由来）は対応なし", () => {
    expect(stmtsForRanges(MAP, [])).toEqual([]);
  });

  it("命令の行から最も内側の文を引ける", () => {
    expect(stmtForLine(MAP, 6)).toEqual(ASSIGN);
    // 14–16 行は return / block / if が重なる。いちばん狭いものを選ぶ
    expect(stmtForLine(MAP, 15)).toEqual(RETURN);
    expect(stmtForLine(MAP, 11)).toEqual(IF);
    expect(stmtForLine(MAP, 99)).toBeNull();
  });
});

// ---- A3 式単位（T144 追補）----
// int main() { a[i] = a[i] + 1; return 0; } を模した対応表。
// 行番号は「左辺のアドレス計算 → 右辺の評価 → 書き込み」の実際の並びに合わせてある。
const E_LHS_I: SpanEntry = { sourceRanges: [{ from: 15, to: 16 }], fromLine: 3, toLine: 3 };
const E_LHS_IDX: SpanEntry = { sourceRanges: [{ from: 13, to: 17 }], fromLine: 1, toLine: 4 };
// 右辺の a[i] は「アドレス計算だけ」と「読み出しまで」の2件が同じ範囲で載る（PtrArith + Rval）
const E_RHS_IDX_ADDR: SpanEntry = { sourceRanges: [{ from: 20, to: 24 }], fromLine: 5, toLine: 8 };
const E_RHS_IDX_LOAD: SpanEntry = { sourceRanges: [{ from: 20, to: 24 }], fromLine: 5, toLine: 9 };
const E_ONE: SpanEntry = { sourceRanges: [{ from: 27, to: 28 }], fromLine: 10, toLine: 10 };
const E_ADD: SpanEntry = { sourceRanges: [{ from: 20, to: 28 }], fromLine: 5, toLine: 11 };
const E_ASSIGN: SpanEntry = { sourceRanges: [{ from: 13, to: 28 }], fromLine: 1, toLine: 12 };
const E_ZERO: SpanEntry = { sourceRanges: [{ from: 37, to: 38 }], fromLine: 13, toLine: 13 };
const EXPR_MAP = [
  E_LHS_I,
  E_LHS_IDX,
  E_RHS_IDX_ADDR,
  E_RHS_IDX_LOAD,
  E_ONE,
  E_ADD,
  E_ASSIGN,
  E_ZERO,
];
const S_ASSIGN: SpanEntry = { sourceRanges: [{ from: 13, to: 29 }], fromLine: 1, toLine: 12 };
const S_RETURN: SpanEntry = { sourceRanges: [{ from: 30, to: 39 }], fromLine: 13, toLine: 15 };
const STMT_MAP = [S_ASSIGN, S_RETURN];

describe("AST ノード ↔ 命令の対応（式単位）", () => {
  it("規則1: 外形が一致する式の命令だけを光らせる", () => {
    // a[i] + 1 を選ぶと右辺の加算列だけ（左辺のアドレス計算 1–4 行は入らない）
    expect(spansForRanges(STMT_MAP, EXPR_MAP, [{ from: 20, to: 28 }])).toEqual([E_ADD]);
  });

  it("規則1: 同じ範囲の重複エントリは全部返す（和が読み出しまで届く）", () => {
    const hits = spansForRanges(STMT_MAP, EXPR_MAP, [{ from: 20, to: 24 }]);
    expect(hits).toEqual([E_RHS_IDX_ADDR, E_RHS_IDX_LOAD]);
    expect(Math.max(...hits.map((e) => e.toLine))).toBe(9); // 読み出しの行まで含む
  });

  it("規則2: 文以上の大きさのノードは含まれる文をすべて集める", () => {
    expect(spansForRanges(STMT_MAP, EXPR_MAP, [{ from: 0, to: 50 }])).toEqual(STMT_MAP);
    // 文そのものの挙動は文単位のときと変わらない
    expect(spansForRanges(STMT_MAP, EXPR_MAP, [{ from: 13, to: 29 }])).toEqual([S_ASSIGN]);
    expect(spansForRanges(STMT_MAP, EXPR_MAP, [{ from: 13, to: 29 }])).toEqual(
      stmtsForRanges(STMT_MAP, [{ from: 13, to: 29 }]),
    );
  });

  it("規則3: 命令を出さない位置は、それを含む最小のエントリに落ちる", () => {
    // 代入左辺の変数名（span を持たない lval）→ 囲む Assign 式
    expect(spansForRanges(STMT_MAP, [E_ASSIGN, E_ADD], [{ from: 13, to: 14 }])).toEqual([E_ASSIGN]);
    // 式が 1 件も無ければ文へ落ちる（文単位のときと同じ）
    expect(spansForRanges(STMT_MAP, [], [{ from: 13, to: 14 }])).toEqual([S_ASSIGN]);
  });

  it("範囲を持たないノード（マクロ展開由来）は対応なし", () => {
    expect(spansForRanges(STMT_MAP, EXPR_MAP, [])).toEqual([]);
    expect(E_LHS_IDX.fromLine).toBe(1); // 左辺の式も表に載っている（未使用警告よけ）
  });

  it("命令の行から最も内側の式を引ける", () => {
    // 読み出しの行（9）は右辺 a[i]。文（1–12）ではなく式が返る
    expect(spanForLine(STMT_MAP, EXPR_MAP, 9)).toEqual(E_RHS_IDX_LOAD);
    // 8 行目は「アドレス計算だけ」の側のほうが行範囲が狭い
    expect(spanForLine(STMT_MAP, EXPR_MAP, 8)).toEqual(E_RHS_IDX_ADDR);
    expect(spanForLine(STMT_MAP, EXPR_MAP, 3)).toEqual(E_LHS_I);
    // 12 行目は Assign 式と代入文が同じ行範囲。ソース範囲の狭い式が勝つ
    expect(spanForLine(STMT_MAP, EXPR_MAP, 12)).toEqual(E_ASSIGN);
    // 式が届かない行（return 文の後始末など）は文へ落ちる
    expect(spanForLine(STMT_MAP, EXPR_MAP, 15)).toEqual(S_RETURN);
    expect(spanForLine(STMT_MAP, EXPR_MAP, 99)).toBeNull();
  });
});

// ---- 実データでの照合（コアの compile / parse を実際に通す）----
// 支援 AST（ツリーの出所）と参考実装の式範囲が本当に一致するか、
// 規則1 で引けているか（フォールバック頼みになっていないか）をここで確かめる。

interface CoreApi {
  parse(s: string): string;
  compile(s: string, comments: boolean): string;
}
const require_ = createRequire(import.meta.url);
const mod = require_("../../core/_build/default/js/api.bc.js") as { myccCore?: CoreApi };
const core: CoreApi = mod.myccCore ?? (globalThis as unknown as { myccCore: CoreApi }).myccCore;

const SRC = [
  '#include "lib.h"',
  "int main() {",
  "    int *a;",
  "    int i;",
  "    a = malloc(sizeof(int) * 3);",
  "    i = 1;",
  "    a[i] = a[i] + 1;",
  "    return a[i];",
  "}",
  "",
].join("\n");

function allNodes(nodes: AstNode[]): AstNode[] {
  const out: AstNode[] = [];
  const walk = (n: AstNode): void => {
    out.push(n);
    for (const v of Object.values(n as unknown as Record<string, unknown>)) {
      if (Array.isArray(v)) {
        for (const x of v) if (x && (x as AstNode).kind) walk(x as AstNode);
      } else if (v && typeof v === "object" && (v as AstNode).kind) {
        walk(v as AstNode);
      }
    }
  };
  nodes.forEach(walk);
  return out;
}

describe("式単位の対応（コアの実データ）", () => {
  const compiled = JSON.parse(core.compile(SRC, false)) as CompileResult;
  const parsed = JSON.parse(core.parse(SRC)) as ParseResult;
  const asm = (compiled.text ?? "").split("\n");
  const stmtMap = compiled.stmtMap ?? [];
  const exprMap = compiled.exprMap ?? [];
  const nodes = allNodes(parsed.ast ?? []);
  const text = (e: { sourceRanges: SourceRange[] }): string =>
    e.sourceRanges.map(({ from, to }) => SRC.slice(from, to)).join("");
  const hitLines = (hits: SpanEntry[]): number[] => {
    const set = new Set<number>();
    for (const e of hits) for (let n = e.fromLine; n <= e.toLine; n += 1) set.add(n);
    return [...set].sort((a, b) => a - b);
  };
  const key = (rs: SourceRange[]): string => {
    const r = outerRange(rs)!;
    return `${r.from}-${r.to}`;
  };
  const indexes = nodes.filter((n) => n.kind === "Index");
  const lhsIndex = indexes[0]!; // a[i] = ... の左辺
  const rhsIndex = indexes[1]!; // ... = a[i] + 1 の左項
  const add = nodes.find((n) => n.kind === "Add")!;
  const assignStmt = nodes.filter((n) => n.kind === "ExprStmt")[2]!;

  it("compile が exprMap を返し、行範囲・ソース範囲が型どおり", () => {
    expect(compiled.ok).toBe(true);
    expect(exprMap.length).toBeGreaterThan(0);
    for (const e of exprMap) {
      expect(Number.isInteger(e.fromLine)).toBe(true);
      expect(e.fromLine).toBeGreaterThan(0);
      expect(e.toLine).toBeGreaterThanOrEqual(e.fromLine);
      expect(e.toLine).toBeLessThanOrEqual(asm.length);
      for (const r of e.sourceRanges) {
        expect(r.to).toBeGreaterThan(r.from);
        expect(r.to).toBeLessThanOrEqual(SRC.length);
      }
    }
  });

  it("(a) 加算ノードを選ぶと右辺の加算列だけが光る", () => {
    const hits = spansForRanges(stmtMap, exprMap, add.sourceRanges!);
    expect(hits.map(text)).toEqual(["a[i] + 1"]);
    const lines = hitLines(hits);
    expect(asm[lines[lines.length - 1]! - 1]).toContain("add ");
    // 代入文の先頭（左辺のアドレス計算）も末尾（書き込み）も含まない
    const stmt = stmtMap.find((e) => text(e) === "a[i] = a[i] + 1;")!;
    expect(lines[0]).toBeGreaterThan(stmt.fromLine);
    expect(lines[lines.length - 1]).toBeLessThan(stmt.toLine);
  });

  it("(b) 右辺の a[i] を選ぶと読み出しの行まで光る", () => {
    const hits = spansForRanges(stmtMap, exprMap, rhsIndex.sourceRanges!);
    expect(hits.length).toBe(2); // アドレス計算だけの式と、読み出しまでの式
    expect(hits.map(text)).toEqual(["a[i]", "a[i]"]);
    const lines = hitLines(hits);
    expect(asm[lines[lines.length - 1]! - 1]).toContain("lw ");
    // 左辺の a[i] は代入先なので読み出さない（右辺より前で終わる）
    const lhsHits = spansForRanges(stmtMap, exprMap, lhsIndex.sourceRanges!);
    expect(lhsHits.length).toBe(1);
    expect(hitLines(lhsHits).at(-1)).toBeLessThan(lines[0]!);
  });

  it("(c) 読み出しの行をクリックすると a[i] のソース範囲が引ける", () => {
    const hits = spansForRanges(stmtMap, exprMap, rhsIndex.sourceRanges!);
    const loadLine = Math.max(...hits.map((e) => e.toLine));
    const back = spanForLine(stmtMap, exprMap, loadLine);
    expect(text(back!)).toBe("a[i]");
    expect(back!.sourceRanges).toEqual(rhsIndex.sourceRanges);
  });

  it("(d) 文ノード・ブロックの挙動は文単位のときと同じ", () => {
    for (const node of [assignStmt, nodes.find((n) => n.kind === "Block")!]) {
      expect(spansForRanges(stmtMap, exprMap, node.sourceRanges!)).toEqual(
        stmtsForRanges(stmtMap, node.sourceRanges!),
      );
    }
  });

  it("式ノードは規則1（完全一致）で引ける。落ちるのは代入左辺の変数だけ", () => {
    const exprKinds = new Set(["Num", "Var", "Add", "Mul", "Index", "Assign", "Call", "SizeofType"]);
    const exact = new Set(exprMap.map((e) => key(e.sourceRanges)));
    const missing = nodes
      .filter((n) => exprKinds.has(n.kind) && n.sourceRanges)
      .filter((n) => !exact.has(key(n.sourceRanges!)));
    // a = malloc(...) と i = 1 の左辺の変数（lval なので式の span を持たない）
    expect(missing.map((n) => text({ sourceRanges: n.sourceRanges! }))).toEqual(["a", "i"]);
    // それらは規則3 で囲む代入式に落ちる
    for (const n of missing) {
      const hits = spansForRanges(stmtMap, exprMap, n.sourceRanges!);
      expect(hits.length).toBe(1);
      expect(text(hits[0]!)).toContain("=");
    }
  });
});
