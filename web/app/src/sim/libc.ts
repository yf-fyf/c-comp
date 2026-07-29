// libc のシム。
//
// 対象は workbook/docs/language_spec.md の lib.h が宣言する関数のうち、
// 教材のテストが実際に使うものに合わせる。
// プログラム側が同名の関数を定義していれば（発展課題 R2_printf など）
// そちらが優先されるので、ここへは来ない。

/** レジスタ番号（a0 = x10） */
const A0 = 10;

export interface LibcHost {
  get(index: number): bigint;
  set(index: number, value: bigint): void;
  readCString(addr: number): string;
  malloc(size: number): number;
  write(text: string): void;
  exit(code: number): void;
}

const SHIMS: Record<string, (h: LibcHost) => void> = {
  printf(h) {
    const fmt = h.readCString(Number(h.get(A0)));
    let argIndex = 1; // a1 から順に
    const nextArg = (): bigint => h.get(A0 + argIndex++);
    let out = "";
    for (let i = 0; i < fmt.length; i++) {
      if (fmt[i] !== "%") {
        out += fmt[i];
        continue;
      }
      i++;
      // 幅・精度・長さ修飾子は読み飛ばす（%5d や %ld を素通しさせる）
      while (i < fmt.length && /[-+ #0-9.lhz]/.test(fmt[i]!)) i++;
      const conv = fmt[i];
      switch (conv) {
        case "d":
        case "i":
          out += BigInt.asIntN(32, nextArg()).toString();
          break;
        case "u":
          out += BigInt.asUintN(32, nextArg()).toString();
          break;
        case "x":
          out += BigInt.asUintN(32, nextArg()).toString(16);
          break;
        case "c":
          out += String.fromCharCode(Number(BigInt.asUintN(8, nextArg())));
          break;
        case "s":
          out += h.readCString(Number(nextArg()));
          break;
        case "%":
          out += "%";
          break;
        default:
          out += `%${conv ?? ""}`;
      }
    }
    h.write(out);
    h.set(A0, BigInt(out.length));
  },

  malloc(h) {
    h.set(A0, BigInt(h.malloc(Number(h.get(A0)))));
  },

  exit(h) {
    h.exit(Number(BigInt.asIntN(32, h.get(A0))));
  },

  strlen(h) {
    h.set(A0, BigInt(h.readCString(Number(h.get(A0))).length));
  },

  strcmp(h) {
    const a = h.readCString(Number(h.get(A0)));
    const b = h.readCString(Number(h.get(A0 + 1)));
    h.set(A0, BigInt(a < b ? -1 : a > b ? 1 : 0));
  },

  strchr(h) {
    const base = Number(h.get(A0));
    const needle = Number(BigInt.asUintN(8, h.get(A0 + 1)));
    const s = h.readCString(base);
    const at = s.indexOf(String.fromCharCode(needle));
    h.set(A0, BigInt(at < 0 ? 0 : base + at));
  },
};

export const isShimName = (name: string): boolean => name in SHIMS;

export const shimNames = (): string[] => Object.keys(SHIMS);

export function callShim(name: string, host: LibcHost): void {
  const fn = SHIMS[name];
  if (!fn) throw new Error(`シムがない: ${name}`);
  fn(host);
}
