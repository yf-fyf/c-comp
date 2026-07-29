// RV64 アセンブリ（参照コンパイラが出す範囲）を実行可能な形に読み込む。
//
// 対象は教材が実際に生成する 29 命令と 8 ディレクティブに限る。
// 未対応の記法はエラーにして行番号を返す（黙って無視しない）。

export const REG_NAMES = [
  "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
  "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
  "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
  "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6",
] as const;

const REG_INDEX = new Map<string, number>();
REG_NAMES.forEach((name, i) => {
  REG_INDEX.set(name, i);
  REG_INDEX.set(`x${i}`, i);
});
REG_INDEX.set("fp", 8); // s0 の別名

/** レジスタ2つと即値を取る算術（rd, rs1, imm） */
const OP_IMM = new Set(["addi", "xori"]);
/** レジスタ3つを取る算術（rd, rs1, rs2） */
const OP_REG = new Set(["add", "sub", "mul", "div", "rem", "and", "or", "xor", "sll", "sra", "slt"]);
/** rd, rs1 の2引数（単項） */
const OP_UNARY = new Set(["neg", "not", "seqz", "snez", "mv"]);
/** メモリ命令。値は幅とゼロ拡張の有無 */
const MEM_OPS: Record<string, { width: 1 | 4 | 8; store: boolean }> = {
  lb: { width: 1, store: false },
  lw: { width: 4, store: false },
  ld: { width: 8, store: false },
  sb: { width: 1, store: true },
  sw: { width: 4, store: true },
  sd: { width: 8, store: true },
};

export interface Insn {
  op: string;
  rd: number;
  rs1: number;
  rs2: number;
  imm: bigint;
  /** メモリ命令のオフセット / 分岐・呼び出しの解決済みアドレス */
  offset: number;
  /** 未解決のラベル名（j / beqz / call / la） */
  target: string | null;
  /** 元のソース行（1 始まり） */
  line: number;
  /** 表示用の元テキスト */
  text: string;
}

export interface DataSymbol {
  name: string;
  addr: number;
  size: number;
  section: "data" | "bss";
}

export interface Program {
  insns: Insn[];
  /** ラベル名 → アドレス（.text はテキスト領域、それ以外はデータ領域） */
  labels: Map<string, number>;
  /** .text 内のラベル（関数名の判定に使う） */
  textLabels: Map<string, number>;
  dataSymbols: DataSymbol[];
  /** データ・bss の初期像（DATA_BASE からの連続領域） */
  dataImage: Uint8Array;
  dataBase: number;
  globals: Set<string>;
}

export class AssembleError extends Error {
  constructor(message: string, readonly line: number) {
    super(message);
  }
}

export const TEXT_BASE = 0x00010000;
export const DATA_BASE = 0x00100000;

const textAddr = (index: number): number => TEXT_BASE + index * 4;
export const textIndex = (addr: number): number => (addr - TEXT_BASE) / 4;

function parseReg(token: string, line: number): number {
  const name = token.trim().replace(/,$/, "");
  const idx = REG_INDEX.get(name);
  if (idx === undefined) throw new AssembleError(`レジスタ名として読めない: '${name}'`, line);
  return idx;
}

function parseImm(token: string, line: number): bigint {
  const t = token.trim().replace(/,$/, "");
  try {
    return BigInt(t);
  } catch {
    throw new AssembleError(`即値として読めない: '${t}'`, line);
  }
}

/** `-8(sp)` を { offset, base } に分ける */
function parseMemOperand(token: string, line: number): { offset: number; base: number } {
  const m = /^(-?\d*)\(([a-z0-9]+)\)$/.exec(token.trim());
  if (!m) throw new AssembleError(`メモリオペランドとして読めない: '${token}'`, line);
  return { offset: m[1] ? Number(m[1]) : 0, base: parseReg(m[2]!, line) };
}

function splitOperands(rest: string): string[] {
  return rest
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

const blank = (line: number, text: string): Insn => ({
  op: "", rd: 0, rs1: 0, rs2: 0, imm: 0n, offset: 0, target: null, line, text,
});

export function assemble(source: string): Program {
  const insns: Insn[] = [];
  const labels = new Map<string, number>();
  const textLabels = new Map<string, number>();
  const dataSymbols: DataSymbol[] = [];
  const globals = new Set<string>();
  const dataBytes: number[] = [];
  let section: "text" | "data" | "bss" = "text";
  let pendingLabel: string | null = null;

  const dataAddr = (): number => DATA_BASE + dataBytes.length;
  const emitBytes = (value: bigint, width: number): void => {
    let v = BigInt.asUintN(width * 8, value);
    for (let i = 0; i < width; i++) {
      dataBytes.push(Number(v & 0xffn));
      v >>= 8n;
    }
  };
  const closeSymbol = (): void => {
    if (dataSymbols.length > 0) {
      const last = dataSymbols[dataSymbols.length - 1]!;
      if (last.size === 0) last.size = dataAddr() - last.addr;
    }
  };

  const rawLines = source.split("\n");
  for (let i = 0; i < rawLines.length; i++) {
    const lineNo = i + 1;
    const raw = rawLines[i]!;
    const withoutComment = raw.replace(/[#;].*$/, "");
    let text = withoutComment.trim();
    if (text === "") continue;

    // 行頭のラベル定義（`main:` や `.L1:`。命令が同じ行に続くこともある）
    const labelMatch = /^([.A-Za-z_][\w.$]*):\s*/.exec(text);
    if (labelMatch) {
      const name = labelMatch[1]!;
      if (section === "text") {
        labels.set(name, textAddr(insns.length));
        textLabels.set(name, textAddr(insns.length));
      } else {
        closeSymbol();
        labels.set(name, dataAddr());
        dataSymbols.push({ name, addr: dataAddr(), size: 0, section });
      }
      pendingLabel = name;
      text = text.slice(labelMatch[0].length).trim();
      if (text === "") continue;
    }

    // ディレクティブ
    if (text.startsWith(".")) {
      const [directive, ...restParts] = text.split(/\s+/);
      const rest = restParts.join(" ").trim();
      switch (directive) {
        case ".text":
        case ".data":
        case ".bss":
          closeSymbol();
          section = directive.slice(1) as typeof section;
          continue;
        case ".globl":
        case ".global":
          globals.add(rest);
          continue;
        case ".byte":
          emitBytes(parseImm(rest, lineNo), 1);
          continue;
        case ".word":
          emitBytes(parseImm(rest, lineNo), 4);
          continue;
        case ".dword":
          emitBytes(parseImm(rest, lineNo), 8);
          continue;
        case ".zero": {
          const n = Number(parseImm(rest, lineNo));
          for (let k = 0; k < n; k++) dataBytes.push(0);
          continue;
        }
        // アセンブラ向けの飾りは読み飛ばす（意味論に影響しない）
        case ".align":
        case ".balign":
        case ".p2align":
        case ".size":
        case ".type":
        case ".section":
        case ".file":
        case ".ident":
        case ".attribute":
        case ".option":
          continue;
        default:
          throw new AssembleError(`未対応のディレクティブ: ${directive}`, lineNo);
      }
    }

    if (section !== "text") {
      throw new AssembleError(`データ領域に命令がある: '${text}'`, lineNo);
    }
    insns.push(parseInsn(text, lineNo));
    pendingLabel = null;
  }
  closeSymbol();
  void pendingLabel;

  // ラベル参照の解決
  for (const insn of insns) {
    if (insn.target === null) continue;
    const addr = labels.get(insn.target);
    if (addr === undefined) {
      // call の飛び先が未定義ならライブラリのシムに回す（machine 側で判断する）
      if (insn.op === "call") continue;
      throw new AssembleError(`未定義のラベル: '${insn.target}'`, insn.line);
    }
    insn.offset = addr;
  }

  return {
    insns,
    labels,
    textLabels,
    dataSymbols,
    dataImage: Uint8Array.from(dataBytes),
    dataBase: DATA_BASE,
    globals,
  };
}

function parseInsn(text: string, line: number): Insn {
  const spaceAt = text.search(/\s/);
  const op = (spaceAt < 0 ? text : text.slice(0, spaceAt)).toLowerCase();
  const rest = spaceAt < 0 ? "" : text.slice(spaceAt + 1).trim();
  const ops = splitOperands(rest);
  const insn = blank(line, text);
  insn.op = op;

  const need = (n: number): void => {
    if (ops.length !== n) {
      throw new AssembleError(`${op} はオペランド${n}個をとる（${ops.length}個あった）`, line);
    }
  };

  if (OP_REG.has(op)) {
    need(3);
    insn.rd = parseReg(ops[0]!, line);
    insn.rs1 = parseReg(ops[1]!, line);
    insn.rs2 = parseReg(ops[2]!, line);
    return insn;
  }
  if (OP_IMM.has(op)) {
    need(3);
    insn.rd = parseReg(ops[0]!, line);
    insn.rs1 = parseReg(ops[1]!, line);
    insn.imm = parseImm(ops[2]!, line);
    return insn;
  }
  if (OP_UNARY.has(op)) {
    need(2);
    insn.rd = parseReg(ops[0]!, line);
    insn.rs1 = parseReg(ops[1]!, line);
    return insn;
  }
  if (op in MEM_OPS) {
    need(2);
    insn.rd = parseReg(ops[0]!, line);
    const mem = parseMemOperand(ops[1]!, line);
    insn.offset = mem.offset;
    insn.rs1 = mem.base;
    return insn;
  }
  switch (op) {
    case "li":
      need(2);
      insn.rd = parseReg(ops[0]!, line);
      insn.imm = parseImm(ops[1]!, line);
      return insn;
    case "la":
      need(2);
      insn.rd = parseReg(ops[0]!, line);
      insn.target = ops[1]!;
      return insn;
    case "beqz":
    case "bnez":
      need(2);
      insn.rs1 = parseReg(ops[0]!, line);
      insn.target = ops[1]!;
      return insn;
    case "j":
    case "call":
    case "jal":
      need(1);
      insn.target = ops[0]!;
      return insn;
    case "ret":
    case "ecall":
      need(0);
      return insn;
    default:
      throw new AssembleError(`未対応の命令: '${op}'`, line);
  }
}
