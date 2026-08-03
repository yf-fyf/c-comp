// OCaml コア (public/core/api.bc.js が定義する globalThis.myccCore) の薄いラッパ。
// 境界は文字列 in / JSON 文字列 out（design/webapps.md 3.3）。
//
// 読み込みは非同期 API として公開する。現状(js_of_ocaml)は api.bc.js がブロッキング
// <script> タグで読み込まれるため myccCore は module 実行時点で既に存在するが、
// 将来 wasm 化(wasm_of_ocaml)すると .wasm の fetch+instantiate が本当に非同期になる
// (T99)。そのときに呼び出し側のAPIを変えずに済むよう、先に非同期化しておく(T129)。
import type { CompileResult, ParseResult, TextResult } from "./types";

interface CoreApi {
  parse(source: string): string;
  astSexp(source: string, showLine: boolean): string;
  astDot(source: string, showLine: boolean): string;
  compile(source: string, comments: boolean): string;
}

const CORE_LOAD_TIMEOUT_MS = 10000;
const CORE_POLL_INTERVAL_MS = 20;

let corePromise: Promise<CoreApi> | null = null;

function waitForCore(): Promise<CoreApi> {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      const c = (globalThis as { myccCore?: CoreApi }).myccCore;
      if (c) {
        resolve(c);
        return;
      }
      if (Date.now() - start > CORE_LOAD_TIMEOUT_MS) {
        reject(new Error("コア (core/api.bc.js) の読み込みがタイムアウトしました"));
        return;
      }
      setTimeout(check, CORE_POLL_INTERVAL_MS);
    };
    check();
  });
}

/** コアの初期化を待つ。ボタンの有効化判定など、呼び出し側が明示的に待ちたい場合用 */
export function coreReady(): Promise<CoreApi> {
  if (!corePromise) corePromise = waitForCore();
  return corePromise;
}

async function guard<T extends { ok: boolean }>(f: (c: CoreApi) => string): Promise<T> {
  try {
    const c = await coreReady();
    return JSON.parse(f(c)) as T;
  } catch (e) {
    // OCaml 例外が JS 例外として漏れた場合（前処理エラーなど）や
    // コア読み込みのタイムアウトもここで受ける
    return { ok: false, errors: [{ message: String(e), line: 0 }] } as unknown as T;
  }
}

export const parseSource = (source: string): Promise<ParseResult> =>
  guard<ParseResult>((c) => c.parse(source));

export const astSexp = (source: string, showLine: boolean): Promise<TextResult> =>
  guard<TextResult>((c) => c.astSexp(source, showLine));

export const astDot = (source: string, showLine: boolean): Promise<TextResult> =>
  guard<TextResult>((c) => c.astDot(source, showLine));

export const compile = (source: string, comments: boolean): Promise<CompileResult> =>
  guard<CompileResult>((c) => c.compile(source, comments));
