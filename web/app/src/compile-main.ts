// A5 ブラウザ内 C コンパイラ（design/webapps.md）。
// 左: エディタ + プリセット、右: 生成された RV64 アセンブリ。
// 出すのは OCaml 参照実装の出力で、学生自身のコンパイラの出力ではない。
import { EditorView, basicSetup } from "codemirror";
import { keymap } from "@codemirror/view";
import { Prec } from "@codemirror/state";
import { cpp } from "@codemirror/lang-cpp";
import { compile, coreReady } from "./core";
import { el as $, mountShell } from "./shell";
import type { ExampleGroup } from "./types";
import "./style.css";

mountShell("compile.html");

// 自動コンパイルの設定は文字サイズ（shell.ts の mycc-font-size）と同じ流儀で持ち越す
const AUTO_KEY = "mycc-auto-compile";
const PLACEHOLDER =
  "ここに生成された RV64 アセンブリが出ます。\n［コンパイル］（Ctrl+Enter）を押してください。";

const editor = new EditorView({
  parent: $("editor"),
  extensions: [
    // basicSetup の defaultKeymap も Mod-Enter を使う（insertBlankLine）ので優先度で勝たせる
    Prec.highest(
      keymap.of([
        {
          key: "Mod-Enter",
          run: () => {
            runCompile();
            return true;
          },
        },
      ]),
    ),
    basicSetup,
    cpp(),
    EditorView.updateListener.of((u) => {
      if (u.docChanged) markDirty();
    }),
  ],
});

// ---- コンパイルと表示 ----

const autoBox = $<HTMLInputElement>("opt-auto");
const button = $<HTMLButtonElement>("btn-compile");
let auto = localStorage.getItem(AUTO_KEY) === "1";
// 一度でもコンパイル結果を出したか。まだなら右ペインは案内文のまま
let hasOutput = false;
let timer: ReturnType<typeof setTimeout> | undefined;

function setStatus(cls: string, text: string): void {
  const status = $("status");
  status.className = cls;
  status.textContent = text;
}

/** ソースまたはオプションが変わった。自動コンパイルが入なら走らせ、切なら「未反映」を示す */
function markDirty(): void {
  if (auto) {
    clearTimeout(timer);
    timer = setTimeout(runCompile, 250);
    return;
  }
  clearTimeout(timer);
  button.classList.add("dirty");
  if (hasOutput) {
    // 表示中のアセンブリは今のソースの出力ではない、と分かるようにする
    $("asm-output").classList.add("stale");
    setStatus("pending", "● 変更あり — ［コンパイル］（Ctrl+Enter）で更新");
  } else {
    setStatus("pending", "［コンパイル］（Ctrl+Enter）でアセンブリを生成します");
  }
}

async function runCompile(): Promise<void> {
  clearTimeout(timer);
  button.classList.remove("dirty");
  const src = editor.state.doc.toString();
  const comments = $<HTMLInputElement>("opt-comments").checked;
  const result = await compile(src, comments);
  const out = $("asm-output");
  if (result.ok) {
    const text = result.text ?? "";
    out.textContent = text;
    out.classList.remove("stale", "placeholder");
    hasOutput = true;
    const lines = text === "" ? 0 : text.split("\n").length;
    setStatus("ok", `✓ コンパイル成功（${lines} 行）`);
  } else {
    // 直前の成功結果は消さずに薄く残す。入力途中の一時的なエラーで
    // 右ペインが点滅しないようにしつつ、古い出力だと分かるようにする。
    if (hasOutput) out.classList.add("stale");
    const err = result.errors?.[0];
    // line は前処理後の行番号（TextResult に行対応表は無い）。0 = 不明。
    // col は行頭からのバイト数（1 起点）で、取れないフェーズ（前処理）では 0 になる。
    let where = "";
    if (err && err.line) {
      where = err.col ? `（${err.line} 行 ${err.col} 桁）` : `（${err.line} 行目）`;
    }
    setStatus("err", `✗ ${err?.message ?? "エラー"}${where}`);
  }
}

button.addEventListener("click", runCompile);
$("opt-comments").addEventListener("change", markDirty);

autoBox.checked = auto;
autoBox.addEventListener("change", () => {
  auto = autoBox.checked;
  localStorage.setItem(AUTO_KEY, auto ? "1" : "0");
  if (auto) runCompile();
});

// エディタ外（プリセット等）にフォーカスがあるときの Ctrl+Enter。
// エディタ内は上の keymap が処理し preventDefault 済みなので二重に走らせない
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !e.defaultPrevented) {
    e.preventDefault();
    runCompile();
  }
});

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

// 初期表示は案内文にする。読み込んだだけでアセンブリが出ていると
// 「プログラムと出力を並べただけの表」に見え、コンパイルしている実感が出ないため。
// 自動コンパイルを入にしている人だけ、その設定どおり読み込み時にも走る。
$("asm-output").textContent = PLACEHOLDER;
$("asm-output").classList.add("placeholder");

// コア初期化待ちの間はコンパイル操作を無効化する。現状(js_of_ocaml)は
// ブロッキング script タグのため実質即座に解決するが、将来の非同期読み込み(T99)に
// 備えた明示的な待ち状態として用意しておく。
button.disabled = true;
setStatus("pending", "コアを読み込み中…");

void Promise.all([loadExamples(), coreReady()]).then(() => {
  button.disabled = false;
  if (editor.state.doc.length === 0) {
    setSource("int main() {\n    return 1 + 2 * 3;\n}\n");
  }
  if (auto) runCompile();
  else markDirty();
});
