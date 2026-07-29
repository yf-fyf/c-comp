import { StateEffect, StateField } from "@codemirror/state";
import { Decoration, EditorView, type DecorationSet } from "@codemirror/view";
import type { SourceRange } from "./types";

export const setHoverRanges = StateEffect.define<readonly SourceRange[]>();
export const setSelectedRanges = StateEffect.define<readonly SourceRange[]>();

function rangeField(effect: typeof setHoverRanges, cls: string) {
  return StateField.define<DecorationSet>({
    create: () => Decoration.none,
    update(value, tr) {
      if (tr.docChanged) value = Decoration.none;
      for (const e of tr.effects) {
        if (!e.is(effect)) continue;
        const ranges = [...e.value]
          .filter(({ from, to }) => from >= 0 && from < to && to <= tr.state.doc.length)
          .sort((a, b) => a.from - b.from || a.to - b.to)
          .map(({ from, to }) => Decoration.mark({ class: cls }).range(from, to));
        value = Decoration.set(ranges, true);
      }
      return value;
    },
    provide: (field) => EditorView.decorations.from(field),
  });
}

export const hoverRangeField = rangeField(setHoverRanges, "cm-ast-hover");
export const selectedRangeField = rangeField(setSelectedRanges, "cm-ast-selected");
