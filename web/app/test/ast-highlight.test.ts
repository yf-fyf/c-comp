// @vitest-environment jsdom
import { EditorState } from "@codemirror/state";
import { describe, expect, it } from "vitest";
import {
  hoverRangeField,
  selectedRangeField,
  setHoverRanges,
  setSelectedRanges,
  stmtForLine,
  stmtsForRanges,
} from "../src/ast-highlight";
import type { StmtSpan } from "../src/types";

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
