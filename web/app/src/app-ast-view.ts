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
import {
  setHoverRanges,
  setSelectedRanges,
  stmtForLine,
  stmtsForRanges,
} from "./ast-highlight";
import { parseSource, astSexp, compile } from "./core";
import { renderTree, type TreeTarget } from "./tree";
import { el as $ } from "./shell";
import type { ParseResult, SourceRange, StmtSpan } from "./types";

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
  // 選択中のノードそのもの。A3（命令との対応）が範囲とラベルを使う
  let selectedTarget: TreeTarget | null = null;

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
      selectedTarget = null;
      highlightStrip();
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
            selectedTarget = selected;
            highlightStrip();
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

  // ---- A3: 命令との対応（明示操作で開く） ----
  // 常時2ペインにはしない。［命令と対応］を押したときだけ AST の下に命令列を出し、
  // 選んだノードが出した命令を光らせる。対応の粒度は文（compile_json の stmtMap）。
  // アセンブリペインと同じく、開く／更新はすべて明示操作にそろえる（T38 B6）。

  const strip = $("ast-asm-strip");
  const stripLines = $("ast-asm-lines");
  const stripToggle = $<HTMLButtonElement>("btn-ast-asm");
  let stripOpen = false;
  let stmtMap: StmtSpan[] = [];
  let asmLineEls: HTMLElement[] = [];
  // 表示中の命令が今のソースの出力ではない（未コンパイル or ソース変更後）
  let stripStale = true;

  function setStripStatus(text: string): void {
    $("ast-asm-status").textContent = text;
  }

  /** 命令列を1行1要素で描き直す。行をクリックすると、その文のソース範囲を光らせる */
  function renderStripLines(text: string): void {
    stripLines.textContent = "";
    stripLines.classList.remove("stale");
    asmLineEls = [];
    const lines = text === "" ? [] : text.split("\n");
    lines.forEach((line, i) => {
      const div = document.createElement("div");
      div.className = "asm-line";
      div.dataset.line = String(i + 1);
      div.textContent = line === "" ? " " : line;
      div.addEventListener("click", () => {
        const hit = stmtForLine(stmtMap, i + 1);
        editor.dispatch({
          effects: [
            setHoverRanges.of([]),
            setSelectedRanges.of((hit?.sourceRanges ?? []) as readonly SourceRange[]),
          ],
        });
      });
      stripLines.appendChild(div);
      asmLineEls.push(div);
    });
  }

  /** 選択中のノードに合わせて命令行のハイライトを付け直す */
  function highlightStrip(): void {
    for (const el of asmLineEls) el.classList.remove("hit");
    if (!stripOpen || stripStale || asmLineEls.length === 0) return;
    const target = selectedTarget;
    if (!target) {
      setStripStatus("AST 木のノードをクリックすると、その文が出した命令が光ります");
      return;
    }
    const hits = stmtsForRanges(stmtMap, target.sourceRanges);
    if (hits.length === 0) {
      setStripStatus(`${target.label}: 対応する命令はありません`);
      return;
    }
    let first = Infinity;
    let last = 0;
    for (const e of hits) {
      for (let n = e.fromLine; n <= e.toLine; n += 1) asmLineEls[n - 1]?.classList.add("hit");
      first = Math.min(first, e.fromLine);
      last = Math.max(last, e.toLine);
    }
    setStripStatus(`${target.label}: ${first}–${last} 行目（${last - first + 1} 行）`);
    asmLineEls[first - 1]?.scrollIntoView({ block: "nearest" });
  }

  async function runStripCompile(): Promise<void> {
    const comments = $<HTMLInputElement>("opt-comments").checked;
    const result = await compile(editor.state.doc.toString(), comments);
    if (!result.ok) {
      stmtMap = [];
      renderStripLines("");
      stripStale = true;
      setStripStatus(`✗ ${result.errors?.[0]?.message ?? "コンパイルエラー"}`);
      return;
    }
    stmtMap = result.stmtMap ?? [];
    renderStripLines(result.text ?? "");
    stripStale = false;
    highlightStrip();
  }

  function openStrip(): void {
    stripOpen = true;
    strip.hidden = false;
    stripToggle.setAttribute("aria-pressed", "true");
    if (stripStale) void runStripCompile();
    else highlightStrip();
  }

  function closeStrip(): void {
    stripOpen = false;
    strip.hidden = true;
    stripToggle.setAttribute("aria-pressed", "false");
  }

  stripToggle.addEventListener("click", () => (stripOpen ? closeStrip() : openStrip()));
  $("btn-ast-asm-refresh").addEventListener("click", () => void runStripCompile());
  $("btn-ast-asm-close").addEventListener("click", closeStrip);
  $("opt-comments").addEventListener("change", () => {
    // 注記コメントの有無で行番号がずれるので、対応表ごと作り直しになる
    stripStale = true;
    if (stripOpen) void runStripCompile();
  });

  // ---- サブタブ（AST 木 / トークン / S 式） ----
  // ［命令と対応］も #ast-tabs の中にあるので、サブタブは data-ast-tab を持つものだけを見る

  for (const btn of document.querySelectorAll<HTMLButtonElement>("#ast-tabs button[data-ast-tab]")) {
    btn.addEventListener("click", () => {
      editor.dispatch({ effects: setHoverRanges.of([]) });
      activeTab = btn.dataset.astTab ?? "tree";
      document
        .querySelectorAll("#ast-tabs button[data-ast-tab]")
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
    selectedTarget = null;
    // 命令列は明示操作でしか更新しない。古い出力だと分かるようにして［更新］を促す
    stripStale = true;
    for (const el of asmLineEls) el.classList.remove("hit");
    stripLines.classList.add("stale");
    if (stripOpen) setStripStatus("● 変更あり — ［更新］で反映");
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
      selectedTarget = null;
      resetView = true;
    },
  };
}
