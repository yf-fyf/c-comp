// @vitest-environment jsdom
import { EditorState } from "@codemirror/state";
import { describe, expect, it } from "vitest";
import {
  hoverRangeField,
  selectedRangeField,
  setHoverRanges,
  setSelectedRanges,
} from "../src/ast-highlight";

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
