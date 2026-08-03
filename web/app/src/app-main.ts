// 統合ページ（T108 / T136・T137）。
// 「作る」（C を書いて AST とアセンブリを見る）と「動かす」（アセンブリを実行する）の
// 二部屋構成。作るモードの C ソースは1箇所だけで、AST とアセンブリが共有する。
// 動かすモードのアセンブリは独立したバッファで、作るモードからは明示操作でしか渡らない。
//
// このファイルが持つのは外枠だけ——モード切替・URL 同期・エディタ生成・作るモードの
// プリセット——で、3ビューの中身は app-ast-view.ts / app-asm-view.ts / app-run-view.ts にある。
// ビュー同士は直接 import せず、ここがコールバックで橋渡しする（循環 import を避ける）。
import { EditorView, basicSetup } from "codemirror";
import { keymap } from "@codemirror/view";
import { Prec } from "@codemirror/state";
import { cpp } from "@codemirror/lang-cpp";
import { hoverRangeField, selectedRangeField } from "./ast-highlight";
import { errorField, initAstView } from "./app-ast-view";
import { initAsmView, type AsmView } from "./app-asm-view";
import { initRunView } from "./app-run-view";
import { loadCExamples } from "./examples";
import { el as $, mountShell } from "./shell";
import "./style.css";

mountShell("app.html");

type Mode = "build" | "run";

const DEFAULT_C_SOURCE = "int main() {\n    return 1 + 2 * 3;\n}\n";
const DEFAULT_C_EXAMPLE = "sessions/01_interpreter/tests/add_mul.c";

// ---- モード ----

// 切替は hidden のトグルだけ。DOM を作り直すとエディタが二重初期化になる
let mode: Mode = "build";
// モードごとに最後に選んだプリセット。切替時に ?example= を入れ直すために持つ
const lastExample: Record<Mode, string | null> = { build: null, run: null };

// ---- C ソース（作るモードで唯一の状態） ----

// docChanged の購読先。AST の自動解析とアセンブリの「未反映」表示がここに載る
const docChangeListeners: Array<() => void> = [];

function onSourceChange(f: () => void): void {
  docChangeListeners.push(f);
}

// エディタ生成時に keymap から参照したいが、ビューの初期化は
// エディタが出来てからでないと出来ないので、後から差す
let asmView: AsmView | null = null;

const editor = new EditorView({
  parent: $("editor"),
  extensions: [
    // basicSetup の defaultKeymap も Mod-Enter を使う（insertBlankLine）ので優先度で勝たせる
    Prec.highest(
      keymap.of([
        {
          key: "Mod-Enter",
          run: () => {
            asmView?.runCompile();
            return true;
          },
        },
      ]),
    ),
    basicSetup,
    cpp(),
    hoverRangeField,
    selectedRangeField,
    errorField,
    EditorView.updateListener.of((u) => {
      if (u.docChanged) for (const f of docChangeListeners) f();
    }),
  ],
});

// ---- ビュー ----

const astView = initAstView({ editor, onSourceChange });

const runView = initRunView({
  isActive: () => mode === "run",
  onExampleChanged(label) {
    lastExample.run = label;
    syncUrl();
  },
});

asmView = initAsmView({
  editor,
  onSourceChange,
  isActive: () => mode === "build",
  // 明示操作でだけアセンブリを渡す。渡した先へ画面も移す（送った結果がすぐ見える）
  sendToRun(text) {
    runView.setAsmSource(text);
    applyMode("run");
    syncUrl();
  },
});

// ---- モード切替 ----

function applyMode(next: Mode): void {
  mode = next;
  $("mode-build").hidden = next !== "build";
  $("mode-run").hidden = next !== "run";
  for (const btn of document.querySelectorAll<HTMLButtonElement>("#mode-tabs button")) {
    btn.classList.toggle("active", btn.dataset.mode === next);
  }
  // hidden の間は clientHeight / offsetTop が 0 で、幅も高さも決まっていない。
  // 表示に戻った後に描き直さないと、実行中の行が枠外のままになる
  if (next === "run") runView.setActive();
  else astView.setActive();
}

// ?mode=build&example=… で直接開ける（教員デモ用）。
// example はモードごとに意味が違う（作る=C のパス、動かす=サンプルのラベル）ので、
// 必ず mode とセットで解釈する。mode 指定なしの ?example= は作るモードとして読む。
function syncUrl(): void {
  const url = new URL(location.href);
  url.searchParams.set("mode", mode);
  const ex = lastExample[mode];
  if (ex) url.searchParams.set("example", ex);
  else url.searchParams.delete("example");
  history.replaceState(null, "", url);
}

for (const btn of document.querySelectorAll<HTMLButtonElement>("#mode-tabs button")) {
  btn.addEventListener("click", () => {
    applyMode(btn.dataset.mode === "run" ? "run" : "build");
    syncUrl();
  });
}

// ---- 作るモードのタブ（AST / アセンブリ） ----
// AST の中のサブタブ（木・トークン・S 式）は app-ast-view.ts が #ast-tabs / .ast-pane で持つ。
// ここは #right 直下だけを見て、サブペインを巻き込まないようにする。

for (const btn of document.querySelectorAll<HTMLButtonElement>("#tabs button")) {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab ?? "ast";
    document
      .querySelectorAll("#tabs button")
      .forEach((b) => b.classList.toggle("active", b === btn));
    document
      .querySelectorAll<HTMLElement>("#right > .pane")
      .forEach((p) => p.classList.toggle("active", p.id === `pane-${tab}`));
    // 隠れている間は木の描画幅が取れないので、表に出してから描き直す
    if (tab === "ast") astView.setActive();
  });
}

// ---- 作るモードのプリセット ----

function setSource(source: string): void {
  astView.reset();
  editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: source } });
}

async function setupBuildExamples(wanted: string | null): Promise<void> {
  const select = $<HTMLSelectElement>("build-example-select");
  const byPath = await loadCExamples(select);
  select.addEventListener("change", () => {
    const item = byPath.get(select.value);
    if (!item) return;
    lastExample.build = item.path;
    setSource(item.source);
    syncUrl();
  });

  const initial = (wanted && byPath.get(wanted)) ?? byPath.get(DEFAULT_C_EXAMPLE);
  if (initial) {
    select.value = initial.path;
    lastExample.build = initial.path;
    setSource(initial.source);
  } else {
    setSource(DEFAULT_C_SOURCE);
  }
}

// ---- 起動 ----

const params = new URL(location.href).searchParams;
const initialMode: Mode = params.get("mode") === "run" ? "run" : "build";
const initialExample = params.get("example");

applyMode(initialMode);

void Promise.all([
  setupBuildExamples(initialMode === "build" ? initialExample : null),
  runView.start(initialMode === "run" ? initialExample : null),
]).then(async () => {
  syncUrl();
  // ソースが確定してから初回の解析と、コア待ちを解く
  await astView.runParse();
  await asmView!.start();
});
