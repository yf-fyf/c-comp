import { StateEffect, StateField } from "@codemirror/state";
import { Decoration, EditorView, type DecorationSet } from "@codemirror/view";
import type { SourceRange, StmtSpan } from "./types";

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

// ---- A3: AST ノード ↔ 命令のクロスハイライト（対応の粒度は文） ----
// 範囲は行またぎで複数に割れる（前処理の対応表が行ごとに切れるため）ので、
// 包含関係は端どうし——最小の from と最大の to——だけで判定する。

/** 範囲の並びを外側の1区間に畳む。範囲を持たない（マクロ展開由来など）なら null */
export function outerRange(ranges: readonly SourceRange[]): SourceRange | null {
  if (ranges.length === 0) return null;
  let from = Infinity;
  let to = -Infinity;
  for (const r of ranges) {
    from = Math.min(from, r.from);
    to = Math.max(to, r.to);
  }
  return { from, to };
}

/**
 * AST ノードのソース範囲に対応する文を選ぶ。
 * ノードが文を含むなら（Block や関数定義）含まれる文すべて、
 * ノードが文より小さいなら（式や識別子）それを含む最も内側の文 1 つ。
 */
export function stmtsForRanges(
  stmtMap: readonly StmtSpan[],
  ranges: readonly SourceRange[],
): StmtSpan[] {
  const span = outerRange(ranges);
  if (!span) return [];
  const withRange = stmtMap
    .map((entry) => ({ entry, range: outerRange(entry.sourceRanges) }))
    .filter((x): x is { entry: StmtSpan; range: SourceRange } => x.range !== null);
  const inside = withRange.filter((x) => x.range.from >= span.from && x.range.to <= span.to);
  if (inside.length > 0) return inside.map((x) => x.entry);
  const around = withRange
    .filter((x) => x.range.from <= span.from && x.range.to >= span.to)
    .sort((a, b) => a.range.to - a.range.from - (b.range.to - b.range.from));
  return around.length > 0 ? [around[0]!.entry] : [];
}

/** 出力アセンブリの行番号から、その行を出した最も内側の文を引く（命令 → ソースの向き） */
export function stmtForLine(stmtMap: readonly StmtSpan[], line: number): StmtSpan | null {
  const hits = stmtMap
    .filter((e) => e.fromLine <= line && line <= e.toLine)
    .sort((a, b) => a.toLine - a.fromLine - (b.toLine - b.fromLine));
  return hits[0] ?? null;
}
