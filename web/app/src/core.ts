// OCaml コア (public/core/api.bc.js が定義する globalThis.myccCore) の薄いラッパ。
// 境界は文字列 in / JSON 文字列 out（design/webapps.md 3.3）。
import type { ParseResult, TextResult } from "./types";

interface CoreApi {
  parse(source: string): string;
  astSexp(source: string, showLine: boolean): string;
  astDot(source: string, showLine: boolean): string;
  compile(source: string, comments: boolean): string;
}

function core(): CoreApi {
  const c = (globalThis as { myccCore?: CoreApi }).myccCore;
  if (!c) throw new Error("コア (core/api.bc.js) が読み込まれていない");
  return c;
}

function guard<T extends { ok: boolean }>(f: () => string): T {
  try {
    return JSON.parse(f()) as T;
  } catch (e) {
    // OCaml 例外が JS 例外として漏れた場合（前処理エラーなど）もここで受ける
    return { ok: false, errors: [{ message: String(e), line: 0 }] } as unknown as T;
  }
}

export const parseSource = (source: string): ParseResult =>
  guard<ParseResult>(() => core().parse(source));

export const astSexp = (source: string, showLine: boolean): TextResult =>
  guard<TextResult>(() => core().astSexp(source, showLine));

export const astDot = (source: string, showLine: boolean): TextResult =>
  guard<TextResult>(() => core().astDot(source, showLine));

export const compile = (source: string, comments: boolean): TextResult =>
  guard<TextResult>(() => core().compile(source, comments));
