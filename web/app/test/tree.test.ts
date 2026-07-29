// @vitest-environment jsdom
// AST 木描画の DOM スモークテスト（コアの実出力を入力に使う）。
import { describe, expect, it, vi } from "vitest";
import { createRequire } from "node:module";
import { renderTree } from "../src/tree";
import type { ParseResult } from "../src/types";

const require = createRequire(import.meta.url);
const mod = require("../../core/_build/default/js/api.bc.js") as {
  myccCore?: { parse(s: string): string };
};
const core = mod.myccCore ?? (globalThis as unknown as { myccCore: { parse(s: string): string } }).myccCore;

const r = JSON.parse(core.parse("int main() {\n    int x;\n    x = 1;\n    return x > 0;\n}\n")) as ParseResult;

function draw(
  collapsed: Set<string>,
  overrides: Partial<Parameters<typeof renderTree>[2]> = {},
): SVGSVGElement {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg") as SVGSVGElement;
  document.body.appendChild(svg);
  renderTree(svg, r.ast!, {
    collapsed,
    selectedId: null,
    onToggle: () => {},
    onHover: () => {},
    onSelect: () => {},
    resetView: true,
    ...overrides,
  });
  return svg;
}

describe("renderTree", () => {
  it("ノードと辺を描画し、正規化バッジが付く", () => {
    const svg = draw(new Set());
    const nodes = svg.querySelectorAll(".tree-node");
    expect(nodes.length).toBeGreaterThan(6); // Program + funcdef + block + ...
    expect(svg.querySelectorAll(".tree-edge").length).toBe(nodes.length - 1);
    expect(svg.querySelectorAll(".tree-badge").length).toBe(1); // x > 0 → Lt
  });

  it("折り畳みで部分木が消える", () => {
    const all = draw(new Set()).querySelectorAll(".tree-node").length;
    const folded = draw(new Set(["top[0].body"])).querySelectorAll(".tree-node").length;
    expect(folded).toBeLessThan(all);
  });

  it("hoverとクリックで対応範囲を通知する", () => {
    const onHover = vi.fn();
    const onSelect = vi.fn();
    const svg = draw(new Set(), { onHover, onSelect });
    const num = [...svg.querySelectorAll<SVGGElement>(".tree-node")].find(
      (node) => node.querySelector(".tree-kind")?.textContent === "Num",
    )!;

    num.dispatchEvent(new MouseEvent("mouseenter"));
    expect(onHover).toHaveBeenCalledWith(expect.objectContaining({ label: "Num" }));
    num.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ label: "Num" }));
    num.dispatchEvent(new MouseEvent("mouseleave"));
    expect(onHover).toHaveBeenLastCalledWith(null);
  });

  it("折り畳み操作とノード選択を分離する", () => {
    const onToggle = vi.fn();
    const onSelect = vi.fn();
    const svg = draw(new Set(), { onToggle, onSelect });
    const fold = svg.querySelector<SVGGElement>(".tree-fold")!;

    fold.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onToggle).toHaveBeenCalledOnce();
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("ノード操作時はSVGのパンにポインタを捕捉させない", () => {
    const svg = draw(new Set());
    const capture = vi.fn();
    Object.defineProperty(svg, "setPointerCapture", { value: capture });
    const node = svg.querySelector<SVGGElement>(".tree-node")!;

    node.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true }));
    expect(capture).not.toHaveBeenCalled();
  });

  it("固定選択とtreeのARIA属性を描画する", () => {
    const svg = draw(new Set(), { selectedId: "top[0].body" });
    const selected = svg.querySelector<SVGGElement>('[data-node-id="top[0].body"]')!;
    expect(selected.classList.contains("selected")).toBe(true);
    expect(selected.getAttribute("role")).toBe("treeitem");
    expect(selected.getAttribute("aria-selected")).toBe("true");
    expect(selected.getAttribute("aria-expanded")).toBe("true");
  });
});
