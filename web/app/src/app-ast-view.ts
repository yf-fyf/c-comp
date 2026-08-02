// 統合ページの AST ビュー（T137）。移植元は削除済みの ast-main.ts（git 履歴を参照）。
// 移植元との違いは、エディタを自前で作らず統合シェルから受け取る点と、
// サブタブの id を #ast-tabs / .ast-pane にして外側タブ（AST / アセンブリ）と
// 名前空間を分けた点だけ。
//
// 「作る」モードの AST は入力に追随して自動更新する（T38 B6 の水準は
// モードごとに分ける、という T137 の決定。#pane-ast の注記に常掲してある）。
import { EditorView } from "codemirror";
import { StateEffect, StateField } from "@codemirror/state";
import { Decoration, type DecorationSet } from "@codemirror/view";
import { setHoverRanges, setSelectedRanges } from "./ast-highlight";
import { parseSource, astSexp } from "./core";
import { renderTree } from "./tree";
import { el as $ } from "./shell";
import type { ParseResult, SourceRange } from "./types";

// ---- エディタ拡張: エラー行のハイライト ----
// エディタ生成は app-main.ts なので、フィールドだけ作って渡す。

const setErrorLine = StateEffect.define<number | null>();

function lineField(effect: typeof setErrorLine, cls: string) {
  const deco = Decoration.line({ class: cls });
  return StateField.define<DecorationSet>({
    create: () => Decoration.none,
    update(value, tr) {
      value = value.map(tr.changes);
      for (const e of tr.effects) {
        if (e.is(effect)) {
          if (e.value == null || e.value < 1 || e.value > tr.state.doc.lines) {
            value = Decoration.none;
          } else {
            value = Decoration.set([deco.range(tr.state.doc.line(e.value).from)]);
          }
        }
      }
      return value;
    },
    provide: (f) => EditorView.decorations.from(f),
  });
}

/** app-main.ts がエディタの extensions に入れる（移植元の errorField と同じもの） */
export const errorField = lineField(setErrorLine, "cm-ast-error");

export interface AstView {
  /** 解析して描画し直す（起動時とプリセット差し替え後） */
  runParse(): Promise<void>;
  /** タブ／モードで表示に戻ったときの描画やり直し */
  setActive(): void;
  /** プリセットでソースを丸ごと入れ替えたときの表示リセット */
  reset(): void;
}

export interface AstViewOptions {
  editor: EditorView;
  /** C ソースの変更を購読する（app-main.ts の docChangeListeners） */
  onSourceChange(f: () => void): void;
}

export function initAstView(opts: AstViewOptions): AstView {
  const { editor } = opts;

  // ---- 状態 ----

  let result: ParseResult | null = null;
  let ppToSrc = new Map<number, number>();
  const collapsed = new Set<string>();
  let resetView = false;
  let activeTab = "tree";
  let selectedId: string | null = null;

  // ---- 解析と表示 ----

  let timer: ReturnType<typeof setTimeout> | undefined;
  function scheduleParse(): void {
    clearTimeout(timer);
    timer = setTimeout(runParse, 250);
  }

  async function runParse(): Promise<void> {
    editor.dispatch({ effects: setHoverRanges.of([]) });
    const src = editor.state.doc.toString();
    result = await parseSource(src);
    ppToSrc = new Map(result.lineMap ?? []);
    const status = $("status");
    if (result.ok) {
      const nodes = countNodes();
      status.textContent = `✓ 解析成功（トークン ${result.tokens?.length ?? 0}・ノード ${nodes}）`;
      status.className = "ok";
      editor.dispatch({ effects: setErrorLine.of(null) });
    } else {
      selectedId = null;
      editor.dispatch({ effects: setSelectedRanges.of([]) });
      const err = result.errors?.[0];
      const srcLine = err && err.line ? (ppToSrc.get(err.line) ?? null) : null;
      status.textContent =
        `✗ ${err?.message ?? "エラー"}` + (srcLine ? `（${srcLine} 行目）` : "");
      status.className = "err";
      editor.dispatch({ effects: setErrorLine.of(srcLine) });
    }
    await renderActive();
  }

  function countNodes(): number {
    let n = 0;
    const walk = (x: unknown): void => {
      if (Array.isArray(x)) return x.forEach(walk);
      if (x && typeof x === "object") {
        if ("kind" in x) n += 1;
        Object.values(x).forEach(walk);
      }
    };
    walk(result?.ast ?? []);
    return n;
  }

  async function renderActive(): Promise<void> {
    if (!result) return;
    const showLine = $<HTMLInputElement>("opt-show-line").checked;
    const src = editor.state.doc.toString();
    if (activeTab === "tree") {
      if (result.ok && result.ast) {
        renderTree($("tree-svg") as unknown as SVGSVGElement, result.ast, {
          collapsed,
          selectedId,
          onToggle(id) {
            editor.dispatch({ effects: setHoverRanges.of([]) });
            if (collapsed.has(id)) collapsed.delete(id);
            else collapsed.add(id);
            renderActive();
          },
          onHover(target) {
            editor.dispatch({ effects: setHoverRanges.of(target?.sourceRanges ?? []) });
          },
          onSelect(target) {
            const selected = target && target.id !== selectedId ? target : null;
            selectedId = selected?.id ?? null;
            editor.dispatch({
              effects: [
                setHoverRanges.of([]),
                setSelectedRanges.of((selected?.sourceRanges ?? []) as readonly SourceRange[]),
              ],
            });
            renderActive();
          },
          resetView,
        });
        resetView = false;
      }
    } else if (activeTab === "tokens") {
      const tbody = $("token-body");
      tbody.textContent = "";
      for (const t of result.tokens ?? []) {
        const tr = document.createElement("tr");
        const srcLine = ppToSrc.get(t.line);
        tr.innerHTML = `<td>${srcLine ?? "—"}</td><td>${t.kind}</td><td></td>`;
        (tr.lastElementChild as HTMLElement).textContent = t.text;
        tbody.appendChild(tr);
      }
    } else if (activeTab === "sexp") {
      const r = await astSexp(src, showLine);
      $("sexp-pre").textContent = r.ok ? (r.text ?? "") : (r.errors?.[0]?.message ?? "エラー");
    }
  }

  // ---- サブタブ（AST 木 / トークン / S 式） ----

  for (const btn of document.querySelectorAll<HTMLButtonElement>("#ast-tabs button")) {
    btn.addEventListener("click", () => {
      editor.dispatch({ effects: setHoverRanges.of([]) });
      activeTab = btn.dataset.astTab ?? "tree";
      document
        .querySelectorAll("#ast-tabs button")
        .forEach((b) => b.classList.toggle("active", b === btn));
      document
        .querySelectorAll<HTMLElement>(".ast-pane")
        .forEach((p) => p.classList.toggle("active", p.id === `ast-pane-${activeTab}`));
      renderActive();
    });
  }
  $("opt-show-line").addEventListener("change", renderActive);

  // ---- 入力への追随（移植元の updateListener 相当） ----

  opts.onSourceChange(() => {
    selectedId = null;
    scheduleParse();
  });

  return {
    runParse,
    setActive() {
      void renderActive();
    },
    reset() {
      collapsed.clear();
      selectedId = null;
      resetView = true;
    },
  };
}
