// C・構造・命令・実行を同じ作業画面につなぐ。入力が変わったら古い実行対象を停止する。
import { EditorView, basicSetup } from "codemirror";
import { keymap } from "@codemirror/view";
import { Prec } from "@codemirror/state";
import { cpp } from "@codemirror/lang-cpp";
import {
  hoverRangeField, selectedRangeField, executionRangeField,
  setHoverRanges, setSelectedRanges, setExecutionRanges, spanForLine,
} from "./ast-highlight";
import { errorField, initAstView } from "./app-ast-view";
import { initRunView } from "./app-run-view";
import { compile, coreReady } from "./core";
import { loadCExamples } from "./examples";
import { el as $, mountShell } from "./shell";
import type { CompileResult } from "./types";
import "./style.css";

mountShell("app.html");
type View = "ast" | "asm" | "run";
const DEFAULT_C_SOURCE = "int main() {\n    return 1 + 2 * 3;\n}\n";
const DEFAULT_C_EXAMPLE = "sessions/01_interpreter/tests/add_mul.c";
const params = new URL(location.href).searchParams;
const legacyRun = params.get("mode") === "run";
let view: View = params.get("view") === "run" || legacyRun ? "run"
  : params.get("view") === "asm" ? "asm" : "ast";
let cExample: string | null = null;
let asmExample: string | null = null;
let origin: "empty" | "c" | "assembly" = "empty";
let revision = 0;
let request = 0;
let artifact: CompileResult | null = null;
let ready = false;
const listeners: Array<() => void> = [];
const button = $<HTMLButtonElement>("btn-compile");
function status(cls: string, text: string): void {
  $("asm-status").className = cls;
  $("asm-status").textContent = text;
}
const editor = new EditorView({
  parent: $("editor"),
  extensions: [
    Prec.highest(keymap.of([{key: "Mod-Enter", run: () => { void runCompile(); return true; }}])),
    basicSetup, cpp(), hoverRangeField, selectedRangeField, executionRangeField, errorField,
    EditorView.updateListener.of(u => { if (u.docChanged) for (const f of listeners) f(); }),
  ],
});
const onSourceChange = (f: () => void): void => { listeners.push(f); };
const astView = initAstView({editor, onSourceChange, onCompile: () => void runCompile()});
function highlightExecution(line: number | null): void {
  const hit = origin === "c" && artifact && line !== null
    ? spanForLine(artifact.stmtMap ?? [], artifact.exprMap ?? [], line) : null;
  editor.dispatch({effects: setExecutionRanges.of(hit?.sourceRanges ?? [])});
}
const runView = initRunView({
  isActive: () => view === "run",
  onImport(text, label) {
    ++request;
    origin = "assembly";
    artifact = null;
    asmExample = label;
    astView.setCompiled(null);
    editor.dispatch({effects: [setHoverRanges.of([]), setSelectedRanges.of([]), setExecutionRanges.of([])]});
    const ok = runView.setAsmSource(text);
    $("asm-hint").textContent = "行番号でブレークポイント。このCとの対応はありません。";
    $("source-context").textContent = "読み込んだ命令を観察中です。このCとの対応はありません。";
    status(ok ? "ok" : "err", ok
      ? "読み込んだアセンブリの実行準備ができました。このCから生成した命令ではありません。"
      : "アセンブリを読み込めません。命令欄のエラーを確認してください。");
    button.disabled = !ready;
    applyView("run");
    syncUrl();
  },
  onCurrentLine: highlightExecution,
  onLineSelected(line) {
    const hit = origin === "c" && artifact
      ? spanForLine(artifact.stmtMap ?? [], artifact.exprMap ?? [], line) : null;
    editor.dispatch({effects: [setHoverRanges.of([]), setSelectedRanges.of(hit?.sourceRanges ?? [])]});
  },
});
function markDirty(): void {
  ++revision;
  ++request;
  artifact = null;
  astView.setCompiled(null);
  button.classList.add("dirty");
  button.disabled = !ready;
  highlightExecution(null);
  if (origin === "c") {
    $("asm-hint").textContent = "変更未反映。Cとの対応は再コンパイル後に確認できます。";
    runView.invalidate();
    $("source-context").textContent = "変更未反映：表示中の命令・実行状態は編集前のCの結果です。";
    status("pending", "変更未反映 — 実行を停止しました。［コンパイル］で命令と実行準備を更新します。");
  } else if (origin === "empty" && ready) {
    status("pending", "Cを編集し、［コンパイル］で命令生成と実行準備へ進めます。");
  }
}
onSourceChange(markDirty);
$("opt-comments").addEventListener("change", markDirty);
async function runCompile(): Promise<void> {
  if (!ready) return;
  const token = ++request;
  const sourceRevision = revision;
  const src = editor.state.doc.toString();
  artifact = null;
  astView.setCompiled(null);
  runView.invalidate();
  highlightExecution(null);
  button.disabled = true;
  status("pending", "コンパイル中…");
  const result = await compile(src, $<HTMLInputElement>("opt-comments").checked);
  if (token !== request || sourceRevision !== revision) return;
  button.disabled = false;
  if (!result.ok) {
    const err = result.errors?.[0];
    status("err", `コンパイルできません：${err?.message ?? "エラー"}`);
    $("source-context").textContent = "実行は停止中です。残っている命令・観察結果は以前の入力のものです。";
    return;
  }
  origin = "c";
  asmExample = null;
  artifact = result;
  astView.setCompiled(result);
  const ok = runView.setAsmSource(result.text ?? "");
  $("asm-hint").textContent = "行番号でブレークポイント／命令を選ぶとCの対応箇所";
  button.classList.remove("dirty");
  $("source-context").textContent = "このCから生成した命令です。実行時は次の命令に対応する箇所を緑で示します。";
  status(ok ? "ok" : "err", ok
    ? "参照実装でコンパイル成功・実行準備完了 — ［実行を追う］で1命令ずつ確かめられます。"
    : "命令生成は成功しましたが、実行準備に失敗しました。命令欄のエラーを確認してください。");
  syncUrl();
}
button.addEventListener("click", () => void runCompile());
document.addEventListener("keydown", e => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !e.defaultPrevented
      && !$("asm-editor").contains(e.target as Node)) {
    e.preventDefault(); void runCompile();
  }
});
function applyView(next: View): void {
  view = next;
  $("pane-ast").classList.toggle("active", next === "ast");
  $("pane-machine").classList.toggle("active", next !== "ast");
  $("pane-machine").dataset.view = next;
  $("pane-machine").setAttribute("aria-labelledby", next === "run" ? "tab-run" : "tab-asm");
  for (const btn of document.querySelectorAll<HTMLButtonElement>("#tabs button")) {
    const active = btn.dataset.tab === next;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-selected", String(active));
    btn.tabIndex = active ? 0 : -1;
  }
  if (next === "ast") astView.setActive(); else runView.setActive();
}
function syncUrl(): void {
  const url = new URL(location.href);
  url.searchParams.delete("mode"); url.searchParams.delete("example");
  url.searchParams.set("view", view);
  if (cExample) url.searchParams.set("c", cExample); else url.searchParams.delete("c");
  if (origin === "assembly" && asmExample) url.searchParams.set("asm", asmExample);
  else url.searchParams.delete("asm");
  history.replaceState(null, "", url);
}
const tabs = [...document.querySelectorAll<HTMLButtonElement>("#tabs button")];
for (const btn of tabs) {
  btn.addEventListener("click", () => { applyView(btn.dataset.tab as View); syncUrl(); });
  btn.addEventListener("keydown", e => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
    e.preventDefault();
    const index = tabs.indexOf(btn);
    const next = e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1
      : (index + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
    tabs[next]!.click(); tabs[next]!.focus();
  });
}
async function setupExamples(): Promise<void> {
  const select = $<HTMLSelectElement>("build-example-select");
  const byPath = await loadCExamples(select);
  function choose(path: string): void {
    const item = byPath.get(path);
    if (!item) return;
    astView.reset();
    editor.dispatch({changes: {from: 0, to: editor.state.doc.length, insert: item.source}});
    cExample = item.path;
    select.value = item.path;
    syncUrl();
  }
  select.addEventListener("change", () => choose(select.value));
  // 編集済みのCを、教材の未変更サンプルとしてURLに記録しない。
  onSourceChange(() => { cExample = null; select.selectedIndex = -1; syncUrl(); });
  const wanted = params.get("c") ?? (!legacyRun ? params.get("example") : null);
  const initial = (wanted && byPath.get(wanted)) || byPath.get(DEFAULT_C_EXAMPLE);
  if (initial) choose(initial.path);
  else editor.dispatch({changes: {from: 0, to: editor.state.doc.length, insert: DEFAULT_C_SOURCE}});
}
applyView(view);
button.disabled = true;
status("pending", "コアを読み込み中…");
void Promise.all([
  setupExamples(),
  runView.start(params.get("asm") ?? (legacyRun ? params.get("example") : null), legacyRun || params.has("asm")),
  coreReady(),
]).then(async () => {
  ready = true;
  button.disabled = false;
  syncUrl();
  await astView.runParse();
  if (origin === "empty") status("pending", "Cを編集し、［コンパイル］で命令生成と実行準備へ進めます。");
}).catch(e => {
  status("err", `読み込めません：${String(e)}。ページを再読み込みしてください。`);
});
