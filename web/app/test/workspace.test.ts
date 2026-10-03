// @vitest-environment jsdom
// 実際の画面のイベント配線とコア・シミュレータを通して、統合した操作を検査する。
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { EditorView } from "codemirror";

const el = <T extends HTMLElement = HTMLElement>(id: string): T => document.getElementById(id) as T;
const click = (id: string): void => el<HTMLButtonElement>(id).click();
let editor: EditorView;
function source(text: string): void {
  editor.dispatch({changes: {from: 0, to: editor.state.doc.length, insert: text}});
}
async function compile(): Promise<void> {
  click("btn-compile");
  await vi.waitFor(() => expect(el<HTMLButtonElement>("btn-compile").disabled).toBe(false));
}
function observation(): string {
  return ["step-count", "reg-body", "stack-body", "stdout-pre"].map(id => el(id).textContent).join("|");
}
beforeAll(async () => {
  document.body.innerHTML = readFileSync("app.html", "utf8")
    .split("<body class=\"workspace\">")[1]!.split("</body>")[0]!;
  // jsdomにはテキスト配置・ネイティブdialogの実装がない。
  Range.prototype.getClientRects = () => [] as unknown as DOMRectList;
  Range.prototype.getBoundingClientRect = () => new DOMRect();
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
  vi.stubGlobal("fetch", async () => ({json: async () => []}));
  const storage = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
  });
  const require = createRequire(import.meta.url);
  const mod = require("../../core/_build/default/js/api.bc.js");
  vi.stubGlobal("myccCore", mod.myccCore ?? (globalThis as unknown as {myccCore: unknown}).myccCore);
  await import("../src/app-main");
  await vi.waitFor(() => expect(el("status").className).toBe("ok"));
  editor = EditorView.findFromDOM(document.querySelector<HTMLElement>(".cm-editor")!)!;
});
beforeEach(async () => {
  source("int main() { return 7; }");
  await compile();
});

describe("共通の作業画面", () => {
  it("コンパイルだけでは実行せず、同じ命令をステップ・逆ステップできる", () => {
    expect(el("step-count").textContent).toBe("0");
    expect(el<HTMLButtonElement>("btn-step").disabled).toBe(false);
    click("tab-run"); click("btn-step");
    expect(el("step-count").textContent).toBe("1");
    click("btn-back");
    expect(el("step-count").textContent).toBe("0");
    click("btn-run");
    expect(el("exit-code").textContent).toBe("7");
  });
  it("表示の切替でC・命令・実行位置を失わない", () => {
    click("tab-run"); click("btn-step");
    const held = observation();
    click("tab-ast"); click("tab-asm"); click("tab-run");
    expect(observation()).toBe(held);
    expect(editor.state.doc.toString()).toContain("return 7");
    expect(el("editor").closest("[hidden]")).toBe(null);
  });
  it("編集とコンパイル失敗では観察結果を残し、旧プログラムを再開できない", async () => {
    click("tab-run"); click("btn-step");
    const held = observation();
    source("int main() { return 1 + ; }");
    expect(el<HTMLButtonElement>("btn-step").disabled).toBe(true);
    expect(el<HTMLButtonElement>("btn-run").disabled).toBe(true);
    expect(observation()).toBe(held);
    await compile();
    expect(el("asm-status").className).toBe("err");
    click("btn-step"); click("btn-run");
    expect(observation()).toBe(held);
    await vi.waitFor(() => expect(document.querySelectorAll(".tree-node").length).toBe(0));
    expect(el("ast-asm-lines").children.length).toBe(0);
    source("int main() { return 9; }"); await compile();
    expect(el("step-count").textContent).toBe("0");
    click("btn-run"); expect(el("exit-code").textContent).toBe("9");
  });
  it("連続実行中の編集で予約済みの実行処理を止める", async () => {
    source("int main() { int i; i=0; while(1) { i=i+1; } return i; }"); await compile();
    expect(el<HTMLButtonElement>("btn-run").disabled, el("asm-status").textContent + " / " + el("asm-error").textContent).toBe(false);
    click("tab-run"); click("btn-run");
    expect(Number(el("step-count").textContent), el("asm-error").textContent ?? "").toBeGreaterThan(0);
    source("int main() { return 4; }");
    const held = observation();
    await new Promise(resolve => setTimeout(resolve, 30));
    expect(observation()).toBe(held);
    await compile();
    await new Promise(resolve => setTimeout(resolve, 30));
    expect(el("step-count").textContent).toBe("0");
  });
  it("C入力中のn/pを実行ショートカットとして処理しない", () => {
    click("tab-run"); click("btn-step");
    const held = observation();
    for (const key of ["n", "p", "F9", "F10"]) {
      const event = new KeyboardEvent("keydown", {key, bubbles: true, cancelable: true});
      document.querySelector(".cm-content")!.dispatchEvent(event);
      expect(observation()).toBe(held);
      expect(event.defaultPrevented).toBe(false);
    }
  });
  it("自分のアセンブリを読み込むとCとの対応を解除する", () => {
    click("btn-edit");
    el<HTMLTextAreaElement>("asm-input").value = ".text\n.globl main\nmain:\n li a0, 23\n ret\n";
    el("asm-input").dispatchEvent(new Event("input", {bubbles: true}));
    click("btn-load");
    expect(el("source-context").textContent).toContain("このCとの対応はありません");
    expect(el("ast-asm-lines").children.length).toBe(0);
    expect(document.querySelectorAll(".cm-execution,.cm-ast-selected").length).toBe(0);
    click("btn-run"); expect(el("exit-code").textContent).toBe("23");
  });
});
