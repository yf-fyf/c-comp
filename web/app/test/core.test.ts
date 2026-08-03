// コアの JSON 出力が src/types.ts の型どおりであることの実行時検査（1本だけ持つ）。
// スキーマを二重管理しない代わりに、代表入力でキーと型を全数チェックする。
import { describe, expect, it } from "vitest";
import { createRequire } from "node:module";
import type { AstNode, CompileResult, ParseResult, TextResult, Token } from "../src/types";

interface CoreApi {
  parse(s: string): string;
  astSexp(s: string, l: boolean): string;
  compile(s: string, comments: boolean): string;
}

// js_of_ocaml の Js.export は CommonJS では module.exports へ、
// ブラウザでは globalThis へ書く。テストは require の戻り値から取る。
const require = createRequire(import.meta.url);
const mod = require("../../core/_build/default/js/api.bc.js") as { myccCore?: CoreApi };
const core: CoreApi =
  mod.myccCore ?? (globalThis as unknown as { myccCore: CoreApi }).myccCore;

const NODE_KEYS = new Set([
  "kind", "lhs", "rhs", "cond", "then", "else_", "init", "step", "body",
  "operand", "stmts", "args", "params", "val", "sval", "name", "ty_str",
  "type_sexp", "init_expr", "is_arrow", "line",
  "sourceRanges",
]);
const NODE_FIELDS = ["lhs", "rhs", "cond", "then", "else_", "init", "step", "body", "operand", "init_expr"] as const;
const LIST_FIELDS = ["stmts", "args", "params"] as const;

function assertNode(n: AstNode, path: string): void {
  expect(typeof n.kind, `${path}.kind`).toBe("string");
  for (const key of Object.keys(n)) {
    expect(NODE_KEYS.has(key), `${path} の未知キー: ${key}`).toBe(true);
  }
  for (const f of NODE_FIELDS) {
    const v = n[f];
    if (v !== undefined) assertNode(v, `${path}.${f}`);
  }
  for (const f of LIST_FIELDS) {
    const v = n[f];
    if (v !== undefined) {
      expect(Array.isArray(v), `${path}.${f}`).toBe(true);
      v.forEach((c, i) => assertNode(c, `${path}.${f}[${i}]`));
    }
  }
  if (n.val !== undefined) expect(typeof n.val).toBe("number");
  if (n.sval !== undefined) expect(typeof n.sval).toBe("string");
  if (n.name !== undefined) expect(typeof n.name).toBe("string");
  if (n.ty_str !== undefined) expect(typeof n.ty_str).toBe("string");
  if (n.type_sexp !== undefined) expect(typeof n.type_sexp).toBe("string");
  if (n.is_arrow !== undefined) expect(typeof n.is_arrow).toBe("boolean");
  if (n.line !== undefined) expect(typeof n.line).toBe("number");
  for (const range of n.sourceRanges ?? []) {
    expect(Number.isInteger(range.from)).toBe(true);
    expect(Number.isInteger(range.to)).toBe(true);
    expect(range.from).toBeGreaterThanOrEqual(0);
    expect(range.to).toBeGreaterThan(range.from);
  }
}

function allNodes(nodes: AstNode[]): AstNode[] {
  const result: AstNode[] = [];
  const visit = (node: AstNode): void => {
    result.push(node);
    for (const field of NODE_FIELDS) {
      const child = node[field];
      if (child) visit(child);
    }
    for (const field of LIST_FIELDS) {
      for (const child of node[field] ?? []) visit(child);
    }
  };
  nodes.forEach(visit);
  return result;
}

function sourceText(source: string, node: AstNode): string {
  return (node.sourceRanges ?? []).map(({ from, to }) => source.slice(from, to)).join("");
}

const SAMPLE = `int g;

int add(int a, int b) {
    return a + b;
}

int main() {
    int x;
    x = 3;
    if (x > 2) {
        return add(x, g);
    }
    return 0;
}
`;

describe("myccCore", () => {
  it("parse の JSON が型定義どおり", () => {
    const r = JSON.parse(core.parse(SAMPLE)) as ParseResult;
    expect(r.ok).toBe(true);
    expect(Array.isArray(r.ast)).toBe(true);
    r.ast!.forEach((n, i) => assertNode(n, `ast[${i}]`));
    for (const t of r.tokens as Token[]) {
      expect(["TK_NUM", "TK_CHAR", "TK_STR", "TK_IDENT", "TK_KW", "TK_PUNCT", "TK_EOF"]).toContain(t.kind);
      expect(typeof t.text).toBe("string");
      expect(typeof t.line).toBe("number");
    }
    for (const [pp, src] of r.lineMap!) {
      expect(typeof pp).toBe("number");
      expect(typeof src).toBe("number");
    }
  });

  it("x > 2 が lt の左右入れ替えに正規化される", () => {
    const r = JSON.parse(core.astSexp("int f(int x) { return x > 2; }", false)) as {
      ok: boolean;
      text: string;
    };
    expect(r.ok).toBe(true);
    expect(r.text).toContain("(lt (num 2) (var \"x\"))");
  });

  it("compile の JSON が型定義どおり", () => {
    const r = JSON.parse(core.compile("int main() { return 0; }", false)) as TextResult;
    expect(r.ok).toBe(true);
    expect(typeof r.text).toBe("string");
    expect(r.text).toContain("main:");
  });

  it("compile の stmtMap が文と命令行を結ぶ", () => {
    const source = "int main() {\n    int x;\n    x = 3;\n    return x;\n}\n";
    const r = JSON.parse(core.compile(source, false)) as CompileResult;
    expect(r.ok).toBe(true);
    const lines = (r.text ?? "").split("\n");
    const entries = r.stmtMap!;
    expect(entries.length).toBeGreaterThan(0);
    for (const e of entries) {
      expect(Number.isInteger(e.fromLine)).toBe(true);
      expect(e.fromLine).toBeGreaterThan(0);
      expect(e.toLine).toBeGreaterThanOrEqual(e.fromLine);
      expect(e.toLine).toBeLessThanOrEqual(lines.length);
      for (const range of e.sourceRanges) {
        expect(range.to).toBeGreaterThan(range.from);
        expect(range.to).toBeLessThanOrEqual(source.length);
      }
    }
    const text = (e: { sourceRanges: { from: number; to: number }[] }): string =>
      e.sourceRanges.map(({ from, to }) => source.slice(from, to)).join("");
    const assign = entries.find((e) => text(e) === "x = 3;")!;
    expect(lines.slice(assign.fromLine - 1, assign.toLine).join("\n")).toContain("li a0, 3");
    const ret = entries.find((e) => text(e) === "return x;")!;
    // 文どうしの命令範囲は重ならない（return は代入より後ろ）
    expect(ret.fromLine).toBeGreaterThan(assign.toLine);
  });

  it("compile の exprMap が式と命令行を結ぶ", () => {
    const source = "int main() {\n    int x;\n    x = 1 + 2;\n    return x;\n}\n";
    const r = JSON.parse(core.compile(source, false)) as CompileResult;
    expect(r.ok).toBe(true);
    const lines = (r.text ?? "").split("\n");
    const entries = r.exprMap!;
    expect(entries.length).toBeGreaterThan(0);
    for (const e of entries) {
      expect(Number.isInteger(e.fromLine)).toBe(true);
      expect(e.fromLine).toBeGreaterThan(0);
      expect(e.toLine).toBeGreaterThanOrEqual(e.fromLine);
      expect(e.toLine).toBeLessThanOrEqual(lines.length);
      for (const range of e.sourceRanges) {
        expect(range.to).toBeGreaterThan(range.from);
        expect(range.to).toBeLessThanOrEqual(source.length);
      }
    }
    const text = (e: { sourceRanges: { from: number; to: number }[] }): string =>
      e.sourceRanges.map(({ from, to }) => source.slice(from, to)).join("");
    // 部分式まで載る（文単位の stmtMap には無い粒度）
    const one = entries.find((e) => text(e) === "1")!;
    expect(lines.slice(one.fromLine - 1, one.toLine).join("\n")).toContain("li a0, 1");
    const add = entries.find((e) => text(e) === "1 + 2")!;
    expect(lines.slice(add.fromLine - 1, add.toLine).join("\n")).toContain("add a0");
    // 部分式の命令範囲は、それを含む式の範囲の中に入る
    expect(one.fromLine).toBeGreaterThanOrEqual(add.fromLine);
    expect(one.toLine).toBeLessThanOrEqual(add.toLine);
    // 文の範囲は式より広い（stmtMap は従来どおり文だけ）
    const stmt = r.stmtMap!.find((e) => text(e) === "x = 1 + 2;")!;
    expect(stmt.fromLine).toBeLessThanOrEqual(add.fromLine);
    expect(stmt.toLine).toBeGreaterThanOrEqual(add.toLine);
    expect(r.stmtMap!.some((e) => text(e) === "1 + 2")).toBe(false);
  });

  it("compile のエラーは phase を持つ", () => {
    const r = JSON.parse(core.compile("int main() { return }", false)) as TextResult;
    expect(r.ok).toBe(false);
    expect(["preprocess", "parse", "typing"]).toContain(r.errors![0]!.phase);
    expect(typeof r.errors![0]!.line).toBe("number");
  });

  it("構文エラーはメッセージと行を返す", () => {
    const r = JSON.parse(core.parse("int main() { return }")) as ParseResult;
    expect(r.ok).toBe(false);
    expect(r.errors![0]!.message).toContain("構文解析エラー");
  });

  it("各ノードが構文要素全体の範囲を持つ", () => {
    const source = "// 日本語\nint main() { return (1 + 2 * 3); }";
    const r = JSON.parse(core.parse(source)) as ParseResult;
    const nodes = allNodes(r.ast!);
    const add = nodes.find((n) => n.kind === "Add")!;
    const mul = nodes.find((n) => n.kind === "Mul")!;
    const nums = nodes.filter((n) => n.kind === "Num");

    expect(sourceText(source, add)).toBe("(1 + 2 * 3)");
    expect(sourceText(source, mul)).toBe("2 * 3");
    expect(nums.map((n) => sourceText(source, n))).toEqual(["1", "2", "3"]);
    expect(sourceText(source, r.ast![0]!)).toBe("int main() { return (1 + 2 * 3); }");
  });

  it("正規化で左右が入れ替わっても元の範囲を保つ", () => {
    const source = "int f(int x) { return x > 2; }";
    const r = JSON.parse(core.parse(source)) as ParseResult;
    const lt = allNodes(r.ast!).find((n) => n.kind === "Lt")!;

    expect(sourceText(source, lt)).toBe("x > 2");
    expect(sourceText(source, lt.lhs!)).toBe("2");
    expect(sourceText(source, lt.rhs!)).toBe("x");
  });

  it("macro展開由来のノードには誤った範囲を付けない", () => {
    const source = "#define N 100\nint main() { return N + 1; }";
    const r = JSON.parse(core.parse(source)) as ParseResult;
    const nums = allNodes(r.ast!).filter((n) => n.kind === "Num");
    const expanded = nums.find((n) => n.val === 100)!;
    const direct = nums.find((n) => n.val === 1)!;

    expect(expanded.sourceRanges).toBeUndefined();
    expect(sourceText(source, direct)).toBe("1");
  });

  it("include先には範囲を付けず主ソースの位置を保つ", () => {
    const source = '#include "lib.h"\nint main() { return 0; }';
    const r = JSON.parse(core.parse(source)) as ParseResult;
    const nodes = allNodes(r.ast!);
    const includedProto = nodes.find((n) => n.kind === "FuncProto")!;
    const main = nodes.find((n) => n.kind === "FuncDef" && n.name === "main")!;

    expect(includedProto.sourceRanges).toBeUndefined();
    expect(sourceText(source, main)).toBe("int main() { return 0; }");
  });
});
