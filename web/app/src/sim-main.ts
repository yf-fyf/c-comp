// A2 RV64 シミュレータの画面（design/webapps.md 2.1 A2）。
import { assemble, AssembleError, REG_NAMES, textIndex, type Program } from "./sim/assembler";
import { Machine, MachineError, STACK_TOP, DATA_BASE, REG } from "./sim/machine";
import type { Warning } from "./sim/checks";
import { el as $, mountShell } from "./shell";
import "./style.css";

mountShell("sim.html");

interface SimExample {
  label: string;
  group: string;
  description: string;
  source: string;
  gated: boolean;
}

let program: Program | null = null;
let machine: Machine | null = null;
let sourceLines: string[] = [];
const breakpoints = new Set<number>();
let running = false;
let lastRegs: bigint[] = [];
let fatal: string | null = null;

const hex = (n: number | bigint): string => `0x${n.toString(16)}`;

// ── アセンブリの読み込み ──

function load(text: string): void {
  sourceLines = text.replace(/\n$/, "").split("\n");
  breakpoints.clear();
  fatal = null;
  const errorBox = $("asm-error");
  try {
    program = assemble(text);
    errorBox.hidden = true;
  } catch (e) {
    program = null;
    machine = null;
    errorBox.hidden = false;
    errorBox.textContent =
      e instanceof AssembleError
        ? `${e.line} 行目: ${e.message}`
        : `読み込めない: ${String(e)}`;
    renderAsm();
    return;
  }
  reset();
}

function reset(): void {
  if (!program) return;
  fatal = null;
  try {
    machine = new Machine(program);
    lastRegs = [...machine.regs];
  } catch (e) {
    machine = null;
    fatal = e instanceof MachineError ? e.message : String(e);
  }
  renderAll();
}

// ── 実行 ──

function stepOnce(): boolean {
  if (!machine || machine.halted) return false;
  lastRegs = [...machine.regs];
  try {
    machine.step();
  } catch (e) {
    fatal = e instanceof MachineError ? `${e.line} 行目: ${e.message}` : String(e);
    return false;
  }
  return !machine.halted;
}

function stepBack(): void {
  if (!machine) return;
  fatal = null;
  lastRegs = [...machine.regs];
  machine.stepBack();
  renderAll();
}

/** 停止・ブレークポイント・上限まで走らせる。UI を固めないよう区切って回す */
function run(): void {
  if (!machine || running) return;
  running = true;
  $("btn-stop").hidden = false;
  const tick = (): void => {
    if (!machine || !running) return finishRun();
    for (let i = 0; i < 20000; i++) {
      if (!stepOnce()) return finishRun();
      const line = machine.currentInsn()?.line;
      if (line !== undefined && breakpoints.has(line)) return finishRun();
    }
    renderAll();
    setTimeout(tick, 0);
  };
  tick();
}

function finishRun(): void {
  running = false;
  $("btn-stop").hidden = true;
  renderAll();
}

// ── 描画 ──

function renderAll(): void {
  renderAsm();
  renderRegs();
  renderStack();
  renderData();
  renderWarnings();
  $("stdout-pre").textContent = machine?.stdout ?? "";
  $("step-count").textContent = String(machine?.steps ?? 0);
  const exitBox = $("exit-box");
  exitBox.hidden = machine?.exitCode == null;
  if (machine?.exitCode != null) $("exit-code").textContent = String(machine.exitCode);

  ($("btn-back") as HTMLButtonElement).disabled = !machine || machine.undoLog.length === 0;
  ($("btn-step") as HTMLButtonElement).disabled = !machine || machine.halted;
  ($("btn-run") as HTMLButtonElement).disabled = !machine || machine.halted;
}

/**
 * 行を #asm-view の中だけでスクロールして見せる。
 * scrollIntoView は祖先のスクロール枠（＝ページ全体）まで動かすため使わない。
 * 使うと、すすむたびに画面がコードへ寄ってヘッダと操作ボタンが画面外へ出る。
 */
function scrollLineIntoPane(row: HTMLElement, mode: "nearest" | "center"): void {
  const view = $("asm-view"); // position: relative なので offsetTop はこの枠が基準
  const top = row.offsetTop;
  const bottom = top + row.offsetHeight;
  const slack = (view.clientHeight - row.offsetHeight) / 2;
  if (mode === "center") {
    view.scrollTop = top - slack;
    return;
  }
  // 端に貼り付くと次に実行する命令が見えないので、前後に数行の余裕を残す
  const margin = Math.min(row.offsetHeight * 3, Math.max(slack, 0));
  if (top - margin < view.scrollTop) {
    view.scrollTop = top - margin;
  } else if (bottom + margin > view.scrollTop + view.clientHeight) {
    view.scrollTop = bottom + margin - view.clientHeight;
  }
}

function renderAsm(): void {
  const view = $("asm-view");
  view.textContent = "";
  const currentLine = machine?.currentInsn()?.line ?? -1;

  const frag = document.createDocumentFragment();
  sourceLines.forEach((text, i) => {
    const lineNo = i + 1;
    const row = document.createElement("div");
    row.className = "asm-line";
    if (lineNo === currentLine) row.classList.add("current");
    if (breakpoints.has(lineNo)) row.classList.add("breakpoint");
    if (fatal?.startsWith(`${lineNo} 行目`)) row.classList.add("faulted");

    const gutter = document.createElement("span");
    gutter.className = "asm-gutter";
    gutter.textContent = String(lineNo);
    gutter.addEventListener("click", () => {
      if (breakpoints.has(lineNo)) breakpoints.delete(lineNo);
      else breakpoints.add(lineNo);
      renderAsm();
    });
    const body = document.createElement("span");
    body.className = "asm-text";
    body.textContent = text || " ";
    row.append(gutter, body);
    frag.appendChild(row);
  });
  view.appendChild(frag);

  const active = view.querySelector(".asm-line.current");
  if (active instanceof HTMLElement) scrollLineIntoPane(active, "nearest");

  const box = $("asm-error");
  if (fatal) {
    box.hidden = false;
    box.textContent = fatal;
  } else if (program) {
    box.hidden = true;
  }
}

/** 表示する意味のあるレジスタだけ出す（教材が使う範囲） */
const SHOWN_REGS = [REG.ra, REG.sp, REG.s0, 9, ...Array.from({ length: 8 }, (_, i) => 10 + i)];

function renderRegs(): void {
  const body = $("reg-body");
  body.textContent = "";
  if (!machine) return;
  for (const i of SHOWN_REGS) {
    const value = machine.get(i);
    const tr = document.createElement("tr");
    if (lastRegs[i] !== undefined && lastRegs[i] !== value) tr.className = "changed";
    const name = document.createElement("td");
    name.className = "reg-name";
    name.textContent = REG_NAMES[i]!;
    const dec = document.createElement("td");
    dec.className = "reg-dec";
    dec.textContent = value.toString();
    const as = document.createElement("td");
    as.className = "reg-hex";
    // アドレスらしい値は 16 進のほうが読みやすい
    as.textContent = value > 0xffffn || value < -0xffffn ? hex(BigInt.asUintN(64, value)) : "";
    tr.append(name, dec, as);
    body.appendChild(tr);
  }
}

function renderStack(): void {
  const body = $("stack-body");
  body.textContent = "";
  if (!machine) return;
  const sp = Number(machine.get(REG.sp));
  const s0 = Number(machine.get(REG.s0));
  const top = Math.min(STACK_TOP, Math.max(s0, sp) + 32);
  const bottom = Math.max(sp - 32, top - 8 * 40);
  for (let addr = top - 8; addr >= bottom; addr -= 8) {
    const tr = document.createElement("tr");
    const marks: string[] = [];
    if (addr === sp) marks.push("sp");
    if (addr === s0) marks.push("s0");
    if (addr >= sp && addr < s0) tr.className = "in-frame";
    if (addr < sp) tr.className = "below-sp";

    const a = document.createElement("td");
    a.className = "stack-addr";
    // s0 相対は「学習者がコード中で見る形」なので併記する
    a.textContent = s0 > 0 && addr < s0 ? `${addr - s0}(s0)` : hex(addr);
    const v = document.createElement("td");
    v.className = "stack-val";
    // 表示のための読み出しは peek で行う。load を使うと、画面を描くたびに
    // 「未初期化の領域を読んだ」検査が誤って発火する（描画はプログラムの動作ではない）。
    // int は sw で 4 バイトしか書かれないので、書かれた分だけを幅として表示する
    const written = machine.writtenWidth(addr, 8);
    const width = written >= 8 ? 8 : written >= 4 ? 4 : written >= 1 ? 1 : 0;
    if (width === 0) {
      v.textContent = "—";
      v.classList.add("uninit");
    } else {
      v.textContent = machine.peek(addr, width as 1 | 4 | 8).toString();
      if (width < 8) {
        const note = document.createElement("span");
        note.className = "stack-width";
        note.textContent = `${width}B`;
        note.title = `この番地は下位 ${width} バイトだけが書かれている（int なら 4、char なら 1）`;
        v.append(" ", note);
      }
    }
    const m = document.createElement("td");
    m.className = "stack-mark";
    m.textContent = marks.join(" ");
    tr.append(a, v, m);
    body.appendChild(tr);
  }
}

function renderData(): void {
  const block = $("data-block");
  const body = $("data-body");
  body.textContent = "";
  const symbols = program?.dataSymbols ?? [];
  block.hidden = symbols.length === 0;
  if (!machine || symbols.length === 0) return;
  for (const sym of symbols) {
    const tr = document.createElement("tr");
    const name = document.createElement("td");
    name.className = "data-name";
    name.textContent = sym.name;
    const value = document.createElement("td");
    value.className = "data-value";
    const bytes: number[] = [];
    for (let i = 0; i < Math.min(sym.size, 24); i++) {
      bytes.push(machine.mem[sym.addr - DATA_BASE + i] ?? 0);
    }
    const printable = bytes.length > 0 && bytes.every((b) => b === 0 || (b >= 32 && b < 127));
    value.textContent = printable
      ? JSON.stringify(String.fromCharCode(...bytes.filter((b) => b !== 0)))
      : bytes.map((b) => b.toString(16).padStart(2, "0")).join(" ");
    tr.append(name, value);
    body.appendChild(tr);
  }
}

function renderWarnings(): void {
  const box = $("warnings");
  const list = $("warning-list");
  list.textContent = "";
  const warnings: Warning[] = machine?.warnings ?? [];
  box.hidden = warnings.length === 0;
  for (const w of warnings) {
    const li = document.createElement("li");
    const head = document.createElement("b");
    head.textContent = `${w.line} 行目: `;
    const symptom = document.createElement("span");
    symptom.className = "warn-symptom";
    symptom.textContent = w.symptom;
    li.append(head, document.createTextNode(w.message), document.createElement("br"), symptom);
    li.addEventListener("click", () => {
      const row = $("asm-view").children[w.line - 1];
      if (row instanceof HTMLElement) scrollLineIntoPane(row, "center");
      row?.classList.add("flash");
      setTimeout(() => row?.classList.remove("flash"), 800);
    });
    list.appendChild(li);
  }
}

// ── 操作 ──

$("btn-step").addEventListener("click", () => {
  stepOnce();
  renderAll();
});
$("btn-back").addEventListener("click", stepBack);
$("btn-run").addEventListener("click", run);
$("btn-stop").addEventListener("click", () => {
  running = false;
});
$("btn-reset").addEventListener("click", reset);

const editor = $("asm-editor");
const input = $("asm-input") as HTMLTextAreaElement;
$("btn-edit").addEventListener("click", () => {
  input.value = sourceLines.join("\n");
  editor.hidden = false;
  input.focus();
});
$("btn-cancel").addEventListener("click", () => {
  editor.hidden = true;
});
$("btn-load").addEventListener("click", () => {
  editor.hidden = true;
  load(input.value);
});

// ファイルのドロップでも読める
document.addEventListener("dragover", (e) => e.preventDefault());
document.addEventListener("drop", (e) => {
  e.preventDefault();
  const file = e.dataTransfer?.files?.[0];
  if (!file) return;
  void file.text().then((text) => {
    editor.hidden = true;
    load(text);
  });
});

document.addEventListener("keydown", (e) => {
  if (e.target instanceof HTMLTextAreaElement) return;
  if (e.key === "F10" || (e.key === "n" && !e.ctrlKey)) {
    e.preventDefault();
    stepOnce();
    renderAll();
  } else if (e.key === "F9" || e.key === "p") {
    e.preventDefault();
    stepBack();
  }
});

// ── プリセット ──

const FALLBACK = `# 貼り替えるボタンから自分のアセンブリを読み込める
  .text
  .globl main
main:
  addi sp, sp, -16
  sd ra, 8(sp)
  li a0, 1
  li a1, 2
  add a0, a0, a1
  ld ra, 8(sp)
  addi sp, sp, 16
  ret
`;

async function loadExamples(): Promise<void> {
  const select = $("example-select") as HTMLSelectElement;
  let examples: SimExample[] = [];
  try {
    const res = await fetch("sim-examples.json");
    examples = (await res.json()) as SimExample[];
  } catch {
    load(FALLBACK);
    return;
  }

  const byLabel = new Map<string, SimExample>();
  const groups = new Map<string, HTMLOptGroupElement>();
  for (const ex of examples) {
    // 参照実装の出力は既定で隠す（design/webapps.md 5-2）
    if (ex.gated) continue;
    byLabel.set(ex.label, ex);
    let og = groups.get(ex.group);
    if (!og) {
      og = document.createElement("optgroup");
      og.label = ex.group;
      groups.set(ex.group, og);
      select.appendChild(og);
    }
    const opt = document.createElement("option");
    opt.value = ex.label;
    opt.textContent = ex.description || ex.label;
    og.appendChild(opt);
  }

  const gated = examples.filter((e) => e.gated);
  if (gated.length > 0) addGatedGroup(select, gated, byLabel);

  select.addEventListener("change", () => {
    const ex = byLabel.get(select.value);
    if (!ex) return;
    load(ex.source);
    const url = new URL(location.href);
    url.searchParams.set("example", ex.label);
    history.replaceState(null, "", url);
  });

  const wanted = new URL(location.href).searchParams.get("example");
  const initial = (wanted && byLabel.get(wanted)) ?? [...byLabel.values()][0];
  if (initial) {
    select.value = initial.label;
    load(initial.source);
  } else {
    load(FALLBACK);
  }
}

/** 参照実装の出力は、注意書きに同意してから出す */
function addGatedGroup(
  select: HTMLSelectElement,
  gated: SimExample[],
  byLabel: Map<string, SimExample>,
): void {
  const label = $("example-label");
  const btn = document.createElement("button");
  btn.id = "btn-reveal";
  btn.type = "button";
  btn.textContent = "解答例を見る…";
  btn.addEventListener("click", () => {
    const ok = window.confirm(
      "参照実装（OCaml 版）がこの教材のテストをコンパイルした結果を一覧に加えます。\n\n" +
        "各回の到達目標そのものなので、まず自分で実装してから見ることを勧めます。\n" +
        "（workbook/ocaml/README.md と同じ注意です）",
    );
    if (!ok) return;
    const og = document.createElement("optgroup");
    og.label = "参照実装の出力（解答例）";
    for (const ex of gated) {
      byLabel.set(ex.label, ex);
      const opt = document.createElement("option");
      opt.value = ex.label;
      opt.textContent = ex.description || ex.label;
      og.appendChild(opt);
    }
    select.appendChild(og);
    btn.remove();
  });
  label.appendChild(btn);
}

void loadExamples();
