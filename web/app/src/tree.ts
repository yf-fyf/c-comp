// AST 木の SVG 描画。
// handout の AST 図（parse_viewer.py --format dot）と同じ上下方向・同じ辺ラベルで描く。
// ノード click で部分木の折り畳み、hover でソース行ハイライト（コールバック）。
import { hierarchy, tree } from "d3-hierarchy";
import type { AstNode, SourceRange } from "./types";

interface TNode {
  id: string;          // 根からの経路（折り畳み状態のキー）
  edge: string;        // 親からの辺ラベル（"top[0]" "lhs" "stmts[1]" など）
  label: string;       // kind（根は "Program"）
  sub: string;         // 名前・値・型などの補助表示
  line: number;        // 前処理後の行番号。0 = なし
  sourceRanges: SourceRange[];
  normalized: boolean; // Lt / Le（> >= の正規化で生まれた可能性のあるノード）
  descendants: number; // 折り畳み表示用の子孫数
  children: TNode[];
}

// parse_viewer.py の render_dot と同じフィールド順で子を並べる
const SINGLE_FIELDS: [string, keyof AstNode][] = [
  ["lhs", "lhs"], ["rhs", "rhs"], ["cond", "cond"], ["then", "then"],
  ["else", "else_"], ["init", "init"], ["step", "step"], ["body", "body"],
  ["operand", "operand"], ["init_expr", "init_expr"],
];
const LIST_FIELDS: [string, keyof AstNode][] = [
  ["stmts", "stmts"], ["args", "args"], ["params", "params"],
];

function subLabel(n: AstNode): string {
  const parts: string[] = [];
  if (n.name) parts.push(JSON.stringify(n.name));
  if (n.kind === "Num" && n.val !== undefined) parts.push(String(n.val));
  if (n.kind === "Str" && n.sval !== undefined) parts.push(JSON.stringify(n.sval));
  if (n.kind === "Member") parts.push(n.is_arrow ? "->" : ".");
  if (n.ty_str) parts.push(`: ${n.ty_str}`);
  return parts.join(" ");
}

function build(n: AstNode, id: string, edge: string): TNode {
  const children: TNode[] = [];
  for (const [label, key] of SINGLE_FIELDS) {
    const v = n[key] as AstNode | undefined;
    if (v) children.push(build(v, `${id}.${label}`, label));
  }
  for (const [label, key] of LIST_FIELDS) {
    const vs = (n[key] as AstNode[] | undefined) ?? [];
    vs.forEach((v, i) => children.push(build(v, `${id}.${label}[${i}]`, `${label}[${i}]`)));
  }
  const descendants = children.reduce((a, c) => a + 1 + c.descendants, 0);
  return {
    id,
    edge,
    label: n.kind,
    sub: subLabel(n),
    line: n.line ?? 0,
    sourceRanges: n.sourceRanges ?? [],
    normalized: n.kind === "Lt" || n.kind === "Le",
    descendants,
    children,
  };
}

export interface TreeOptions {
  collapsed: Set<string>;
  selectedId: string | null;
  onToggle(id: string): void;
  onHover(target: TreeTarget | null): void;
  onSelect(target: TreeTarget | null): void;
  /** 入力が変わったときは true にして表示位置をリセットする */
  resetView: boolean;
}

export interface TreeTarget {
  id: string;
  label: string;
  sourceRanges: readonly SourceRange[];
}

const NORMALIZE_NOTE =
  "a > b / a >= b は、構文解析の段階で左右の子を入れ替えた lt / le に正規化される。\n" +
  "このノードはソース上の < <= か、> >= の正規化のどちらかである（S 式と資料の図も同じ表現）。";

interface ViewState {
  x: number;
  y: number;
  w: number;
  h: number;
  interacted: boolean;
}
const viewStates = new WeakMap<SVGSVGElement, ViewState>();

const SVG_NS = "http://www.w3.org/2000/svg";

function el<K extends keyof SVGElementTagNameMap>(
  name: K,
  attrs: Record<string, string | number> = {},
): SVGElementTagNameMap[K] {
  const e = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  return e;
}

export function renderTree(svg: SVGSVGElement, ast: AstNode[], opts: TreeOptions): void {
  const root: TNode = {
    id: "root",
    edge: "",
    label: "Program",
    sub: "",
    line: 0,
    sourceRanges: [],
    normalized: false,
    descendants: 0,
    children: ast.map((n, i) => build(n, `top[${i}]`, `top[${i}]`)),
  };
  root.descendants = root.children.reduce((a, c) => a + 1 + c.descendants, 0);

  const h = hierarchy(root, (d) => (opts.collapsed.has(d.id) ? [] : d.children));
  const layout = tree<TNode>().nodeSize([150, 96]);
  const laid = layout(h);

  svg.textContent = "";
  const viewport = el("g");
  viewport.addEventListener("click", (ev) => {
    if (ev.target === viewport) opts.onSelect(null);
  });
  svg.appendChild(viewport);

  // 辺 + 辺ラベル
  for (const link of laid.links()) {
    const { source: s, target: t } = link;
    viewport.appendChild(
      el("line", {
        class: "tree-edge",
        x1: s.x, y1: s.y + 22, x2: t.x, y2: t.y - 22,
      }),
    );
    const lbl = el("text", {
      class: "tree-edge-label",
      x: (s.x + t.x) / 2,
      y: (s.y + t.y) / 2 + 4,
    });
    lbl.textContent = t.data.edge;
    viewport.appendChild(lbl);
  }

  // ノード
  for (const node of laid.descendants()) {
    const d = node.data;
    const isCollapsed = opts.collapsed.has(d.id) && d.children.length > 0;
    const g = el("g", {
      class: `tree-node${opts.selectedId === d.id ? " selected" : ""}`,
      transform: `translate(${node.x},${node.y})`,
      "data-node-id": d.id,
      role: "treeitem",
      tabindex: 0,
      "aria-level": node.depth + 1,
      "aria-selected": opts.selectedId === d.id ? "true" : "false",
      "aria-label": d.sub ? `${d.label} ${d.sub}` : d.label,
    });

    const textLen = Math.max(d.label.length, d.sub.length, isCollapsed ? 6 : 0);
    const w = Math.min(200, Math.max(70, 18 + textLen * 8));
    g.appendChild(
      el("rect", {
        class: `tree-box${d.line ? "" : " no-line"}${isCollapsed ? " collapsed" : ""}`,
        x: -w / 2, y: -22, width: w, height: 44, rx: 6,
      }),
    );
    const kindText = el("text", { class: "tree-kind", x: 0, y: d.sub || isCollapsed ? -4 : 4 });
    kindText.textContent = d.label;
    g.appendChild(kindText);
    const subContent = isCollapsed ? `… ${d.descendants} ノード` : d.sub;
    if (subContent) {
      const subText = el("text", { class: "tree-sub", x: 0, y: 14 });
      subText.textContent = subContent;
      g.appendChild(subText);
    }

    // Lt / Le: 比較演算子の正規化バッジ
    if (d.normalized) {
      const badge = el("g", { class: "tree-badge", transform: `translate(${w / 2 - 2},-22)` });
      badge.appendChild(el("circle", { r: 9 }));
      const bt = el("text", { y: 4 });
      bt.textContent = "⇄";
      badge.appendChild(bt);
      const title = el("title");
      title.textContent = NORMALIZE_NOTE;
      badge.appendChild(title);
      g.appendChild(badge);
    }

    if (d.children.length > 0) {
      g.setAttribute("aria-expanded", isCollapsed ? "false" : "true");
      const fold = el("g", {
        class: "tree-fold",
        transform: `translate(${-w / 2 + 3},-19)`,
        role: "button",
        tabindex: 0,
        "aria-label": isCollapsed ? "部分木を展開" : "部分木を折り畳み",
      });
      fold.appendChild(el("circle", { r: 8 }));
      const foldText = el("text", { y: 4 });
      foldText.textContent = isCollapsed ? "+" : "−";
      fold.appendChild(foldText);
      const toggle = (ev: Event) => {
        ev.stopPropagation();
        opts.onToggle(d.id);
      };
      fold.addEventListener("click", toggle);
      fold.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          toggle(ev);
        }
      });
      g.appendChild(fold);
    }
    const target: TreeTarget = { id: d.id, label: d.label, sourceRanges: d.sourceRanges };
    g.addEventListener("click", (ev) => {
      ev.stopPropagation();
      opts.onSelect(target);
    });
    g.addEventListener("mouseenter", () => {
      g.classList.add("hovered");
      opts.onHover(target);
    });
    g.addEventListener("mouseleave", () => {
      g.classList.remove("hovered");
      opts.onHover(null);
    });
    g.addEventListener("focus", () => opts.onHover(target));
    g.addEventListener("blur", (ev) => {
      if (!g.contains(ev.relatedTarget as Node | null)) opts.onHover(null);
    });
    g.addEventListener("keydown", (ev) => {
      if (ev.target !== g) return;
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        opts.onSelect(target);
      } else if (ev.key === "Escape") {
        opts.onSelect(null);
      }
    });

    viewport.appendChild(g);
  }

  // 全体が収まる viewBox（ユーザーが動かした後は位置を保持する）
  const xs = laid.descendants().map((n) => n.x);
  const ys = laid.descendants().map((n) => n.y);
  const pad = 120;
  const fit: ViewState = {
    x: Math.min(...xs) - pad,
    y: Math.min(...ys) - 40,
    w: Math.max(...xs) - Math.min(...xs) + pad * 2,
    h: Math.max(...ys) - Math.min(...ys) + 120,
    interacted: false,
  };
  let vs = viewStates.get(svg);
  if (!vs || opts.resetView || !vs.interacted) {
    vs = fit;
    viewStates.set(svg, vs);
    attachPanZoom(svg);
  }
  applyView(svg, vs);
}

function applyView(svg: SVGSVGElement, vs: ViewState): void {
  svg.setAttribute("viewBox", `${vs.x} ${vs.y} ${vs.w} ${vs.h}`);
}

const panZoomAttached = new WeakSet<SVGSVGElement>();

function attachPanZoom(svg: SVGSVGElement): void {
  if (panZoomAttached.has(svg)) return;
  panZoomAttached.add(svg);

  svg.addEventListener(
    "wheel",
    (ev) => {
      ev.preventDefault();
      const vs = viewStates.get(svg);
      if (!vs) return;
      const factor = ev.deltaY > 0 ? 1.15 : 1 / 1.15;
      const rect = svg.getBoundingClientRect();
      const px = vs.x + ((ev.clientX - rect.left) / rect.width) * vs.w;
      const py = vs.y + ((ev.clientY - rect.top) / rect.height) * vs.h;
      vs.x = px - (px - vs.x) * factor;
      vs.y = py - (py - vs.y) * factor;
      vs.w *= factor;
      vs.h *= factor;
      vs.interacted = true;
      applyView(svg, vs);
    },
    { passive: false },
  );

  let dragging: { sx: number; sy: number; ox: number; oy: number } | null = null;
  svg.addEventListener("pointerdown", (ev) => {
    const target = ev.target;
    if (target instanceof Element && target.closest(".tree-node")) return;
    const vs = viewStates.get(svg);
    if (!vs) return;
    dragging = { sx: ev.clientX, sy: ev.clientY, ox: vs.x, oy: vs.y };
    svg.setPointerCapture(ev.pointerId);
  });
  svg.addEventListener("pointermove", (ev) => {
    const vs = viewStates.get(svg);
    if (!dragging || !vs) return;
    const rect = svg.getBoundingClientRect();
    vs.x = dragging.ox - ((ev.clientX - dragging.sx) / rect.width) * vs.w;
    vs.y = dragging.oy - ((ev.clientY - dragging.sy) / rect.height) * vs.h;
    vs.interacted = true;
    applyView(svg, vs);
  });
  svg.addEventListener("pointerup", () => {
    dragging = null;
  });
}
