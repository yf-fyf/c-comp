// A5 ブラウザ内 C コンパイラ（design/webapps.md）。
// 左: エディタ + プリセット、右: 生成された RV64 アセンブリ。
// 出すのは OCaml 参照実装の出力で、学生自身のコンパイラの出力ではない。
import { EditorView, basicSetup } from "codemirror";
import { cpp } from "@codemirror/lang-cpp";
import { compile } from "./core";
import { el as $, mountShell } from "./shell";
import type { ExampleGroup } from "./types";
import "./style.css";

mountShell("compile.html");

const editor = new EditorView({
  parent: $("editor"),
  extensions: [
    basicSetup,
    cpp(),
    EditorView.updateListener.of((u) => {
      if (u.docChanged) scheduleCompile();
    }),
  ],
});

// ---- コンパイルと表示 ----

let timer: ReturnType<typeof setTimeout> | undefined;
function scheduleCompile(): void {
  clearTimeout(timer);
  timer = setTimeout(runCompile, 250);
}

function runCompile(): void {
  const src = editor.state.doc.toString();
  const comments = ($("opt-comments") as HTMLInputElement).checked;
  const result = compile(src, comments);
  const status = $("status");
  const out = $("asm-output");
  if (result.ok) {
    const text = result.text ?? "";
    out.textContent = text;
    out.classList.remove("stale");
    const lines = text === "" ? 0 : text.split("\n").length;
    status.textContent = `✓ コンパイル成功（${lines} 行）`;
    status.className = "ok";
  } else {
    // 直前の成功結果は消さずに薄く残す。入力途中の一時的なエラーで
    // 右ペインが点滅しないようにしつつ、古い出力だと分かるようにする。
    out.classList.add("stale");
    const err = result.errors?.[0];
    // line は前処理後の行番号（TextResult に行対応表は無い）。0 = 不明。
    const where = err && err.line ? `（${err.line} 行目）` : "";
    status.textContent = `✗ ${err?.message ?? "エラー"}${where}`;
    status.className = "err";
  }
}

$("opt-comments").addEventListener("change", runCompile);

// ---- プリセット（workbook/**/tests/*.c からビルド時生成。A1 と同じ examples.json） ----

function setSource(source: string): void {
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

  // ?example=sessions/03_arithmetic_codegen/tests/add.c で直接開ける（教員デモ用）
  const wanted = new URL(location.href).searchParams.get("example");
  const initial =
    (wanted && byPath.get(wanted)) ?? byPath.get("sessions/03_arithmetic_codegen/tests/add.c");
  if (initial) {
    select.value = initial.path;
    setSource(initial.source);
  }
}

void loadExamples().then(() => {
  if (editor.state.doc.length === 0) {
    setSource("int main() {\n    return 1 + 2 * 3;\n}\n");
  }
  runCompile();
});
