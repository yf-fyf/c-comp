// A1 AST ビジュアライザ本体（design/webapps.md 2.1 A1）。
// 左: エディタ + プリセット、右: AST 木 / トークン表 / S 式。
import { EditorView, basicSetup } from "codemirror";
import { cpp } from "@codemirror/lang-cpp";
import { StateEffect, StateField } from "@codemirror/state";
import { Decoration, type DecorationSet } from "@codemirror/view";
import {
  hoverRangeField,
  selectedRangeField,
  setHoverRanges,
  setSelectedRanges,
} from "./ast-highlight";
import { parseSource, astSexp } from "./core";
import { renderTree } from "./tree";
import { el as $, mountShell } from "./shell";
import type { ExampleGroup, ParseResult, SourceRange } from "./types";
import "./style.css";

mountShell("ast.html");

// ---- エディタ: AST範囲とエラー行のハイライト ----

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

const errorField = lineField(setErrorLine, "cm-ast-error");

// ---- 状態 ----

let result: ParseResult | null = null;
let ppToSrc = new Map<number, number>();
const collapsed = new Set<string>();
let resetView = false;
let activeTab = "tree";
let selectedId: string | null = null;

const editor = new EditorView({
  parent: $("editor"),
  extensions: [
    basicSetup,
    cpp(),
    hoverRangeField,
    selectedRangeField,
    errorField,
    EditorView.updateListener.of((u) => {
      if (u.docChanged) {
        selectedId = null;
        scheduleParse();
      }
    }),
  ],
});

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
    status.textContent = `✗ ${err?.message ?? "エラー"}` + (srcLine ? `（${srcLine} 行目）` : "");
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
  const showLine = ($("opt-show-line") as HTMLInputElement).checked;
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

// ---- タブ ----

for (const btn of document.querySelectorAll<HTMLButtonElement>("#tabs button")) {
  btn.addEventListener("click", () => {
    editor.dispatch({ effects: setHoverRanges.of([]) });
    activeTab = btn.dataset.tab ?? "tree";
    document
      .querySelectorAll("#tabs button")
      .forEach((b) => b.classList.toggle("active", b === btn));
    document
      .querySelectorAll<HTMLElement>(".pane")
      .forEach((p) => p.classList.toggle("active", p.id === `pane-${activeTab}`));
    renderActive();
  });
}
$("opt-show-line").addEventListener("change", renderActive);

// ---- プリセット（workbook/**/tests/*.c からビルド時生成） ----

function setSource(source: string): void {
  collapsed.clear();
  selectedId = null;
  resetView = true;
  editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: source } });
}

async function loadExamples(): Promise<void> {
  const select = $("example-select") as HTMLSelectElement;
  let groups: ExampleGroup[] = [];
  try {
    const res = await fetch("examples.json");
    groups = (await res.json()) as ExampleGroup[];
  } catch {
    select.disabled = true;
    return;
  }
  for (const g of groups) {
    const og = document.createElement("optgroup");
    og.label = g.group;
    for (const item of g.items) {
      const opt = document.createElement("option");
      opt.value = item.path;
      opt.textContent = item.label;
      og.appendChild(opt);
    }
    select.appendChild(og);
  }
  const byPath = new Map(groups.flatMap((g) => g.items.map((i) => [i.path, i] as const)));
  select.addEventListener("change", () => {
    const item = byPath.get(select.value);
    if (item) {
      setSource(item.source);
      const url = new URL(location.href);
      url.searchParams.set("example", item.path);
      history.replaceState(null, "", url);
    }
  });

  // ?example=sessions/02_interpreter/tests/add_mul.c で直接開ける（教員デモ用）
  const wanted = new URL(location.href).searchParams.get("example");
  const initial =
    (wanted && byPath.get(wanted)) ?? byPath.get("sessions/02_interpreter/tests/add_mul.c");
  if (initial) {
    select.value = initial.path;
    setSource(initial.source);
  }
}

void loadExamples().then(() => {
  if (editor.state.doc.length === 0) {
    setSource("int main() {\n    return 1 + 2 * 3;\n}\n");
  }
  runParse();
});
