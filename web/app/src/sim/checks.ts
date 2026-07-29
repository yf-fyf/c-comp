// 教育的検査。
//
// workbook/docs/debugging.md の症状表の各行を、実行中に検出できる形に落としたもの。
// どれも警告であって停止ではない。「なぜそれが問題か」を症状表の言葉で返す。

import type { Insn } from "./assembler";

export interface Warning {
  /** ソース行（1 始まり） */
  line: number;
  /** 何命令目で出たか */
  step: number;
  kind: WarningKind;
  message: string;
  /** debugging.md の対応する症状 */
  symptom: string;
}

export type WarningKind =
  | "sp-align"
  | "ra-clobber"
  | "arg-clobber"
  | "uninitialized-read"
  | "below-sp"
  | "caller-frame"
  | "exit-range";

interface Frame {
  name: string;
  raSaved: boolean;
  entrySp: number;
  /** 呼び出し前に立っていた印。戻ったときに呼び出し元の状態へ復す */
  savedClobbered: number[];
}

interface CheckState {
  frames: Frame[];
  clobberedArgs: number[];
  reported: string[];
}

export interface CheckHost {
  get(index: number): bigint;
  steps: number;
  addWarning(w: Warning): void;
}

const A0 = 10;
const A7 = 17;
const SP = 2;
const S0 = 8;
const RA = 1;

const STACK_LOW = 0x00300000;
const STACK_TOP = 0x00400000;

const inStack = (addr: number): boolean => addr >= STACK_LOW && addr < STACK_TOP;

/** 命令が「読む」レジスタ番号を返す */
function readRegisters(insn: Insn): number[] {
  switch (insn.op) {
    case "add": case "sub": case "mul": case "div": case "rem":
    case "and": case "or": case "xor": case "sll": case "sra": case "slt":
      return [insn.rs1, insn.rs2];
    case "addi": case "xori": case "mv": case "neg": case "not":
    case "seqz": case "snez":
      return [insn.rs1];
    case "lb": case "lw": case "ld":
      return [insn.rs1];
    case "sb": case "sw": case "sd":
      return [insn.rs1, insn.rd]; // ベースと、格納する値
    case "beqz": case "bnez":
      return [insn.rs1];
    default:
      return [];
  }
}

export class Checker {
  private frames: Frame[] = [];
  /** 呼び出しをまたいで壊れている可能性のある引数レジスタ */
  private clobberedArgs = new Set<number>();
  /** 同じ内容を何度も出さないための既出キー */
  private reported = new Set<string>();

  constructor(private readonly host: CheckHost) {}

  /** エントリ関数（main か _start）を最初のフレームとして積む */
  enterEntry(name: string, sp: number): void {
    this.frames = [{ name, raSaved: false, entrySp: sp, savedClobbered: [] }];
  }

  snapshot(): CheckState {
    return {
      frames: this.frames.map((f) => ({ ...f })),
      clobberedArgs: [...this.clobberedArgs],
      reported: [...this.reported],
    };
  }

  restore(raw: unknown): void {
    const s = raw as CheckState;
    this.frames = s.frames.map((f) => ({ ...f }));
    this.clobberedArgs = new Set(s.clobberedArgs);
    this.reported = new Set(s.reported);
  }

  private warn(kind: WarningKind, line: number, message: string, symptom: string, key = ""): void {
    const dedup = `${kind}:${line}:${key}`;
    if (this.reported.has(dedup)) return;
    this.reported.add(dedup);
    this.host.addWarning({ line, step: this.host.steps, kind, message, symptom });
  }

  /** 命令の実行直前。壊れている可能性のあるレジスタを読んでいないか見る */
  beforeExecute(insn: Insn): void {
    if (this.clobberedArgs.size === 0) return;
    for (const r of readRegisters(insn)) {
      if (this.clobberedArgs.has(r)) {
        this.warn(
          "arg-clobber",
          insn.line,
          `a${r - A0} を関数呼び出しのあとに読んでいる。` +
            `a0–a7 は呼び出し先が自由に壊してよいレジスタ（caller-saved）なので、` +
            `呼び出しをまたいで値を保ちたいならスタックへ退避する`,
          "再帰の途中で壊れる（引数の退避漏れ）",
          String(r),
        );
        this.clobberedArgs.delete(r);
      }
    }
  }

  /** 値をレジスタからメモリへ書いた（ra の退避を追う） */
  onStoreReg(srcReg: number): void {
    if (srcReg === RA && this.frames.length > 0) {
      this.frames[this.frames.length - 1]!.raSaved = true;
    }
  }

  onCall(name: string, insn: Insn): void {
    const sp = Number(this.host.get(SP));
    if (sp % 16 !== 0) {
      this.warn(
        "sp-align",
        insn.line,
        `call の直前で sp が 16 の倍数になっていない（sp = 0x${sp.toString(16)}、` +
          `余り ${sp % 16}）。RV64 の呼び出し規約はこれを要求する`,
        "Illegal instruction / Bus error（スタックアラインメント違反）",
      );
    }
    const current = this.frames[this.frames.length - 1];
    if (current && !current.raSaved) {
      this.warn(
        "ra-clobber",
        insn.line,
        `${current.name} は ra を退避しないまま call しようとしている。` +
          `call は戻り番地を ra に上書きするので、この関数へは戻れなくなる`,
        "関数から戻ると壊れる（ra の退避漏れ）",
      );
    }
    // 呼び出し先から見た印は空から始める。呼び出し元の分はフレームに預ける
    this.frames.push({
      name, raSaved: false, entrySp: sp, savedClobbered: [...this.clobberedArgs],
    });
    this.clobberedArgs.clear();
  }

  /** 呼び出しから戻った（シムも含む）。呼び出し元の視点に戻す */
  onReturn(): void {
    const frame = this.frames.pop();
    this.clobberedArgs = new Set(frame?.savedClobbered ?? []);
    // a1–a7 は呼び出し先が壊しうる。a0 は戻り値なので対象外
    for (let r = A0 + 1; r <= A7; r++) this.clobberedArgs.add(r);
  }

  /** 値をレジスタへ書いた（引数レジスタなら「壊れている」印を消す） */
  onRegWrite(index: number): void {
    this.clobberedArgs.delete(index);
  }

  onUninitializedRead(addr: number, _width: number, line: number): void {
    if (!inStack(addr)) return;
    this.warn(
      "uninitialized-read",
      line,
      `まだ何も書いていないスタック領域を読んでいる（0x${addr.toString(16)}）。` +
        `初期化していないローカル変数か、フレームの計算違いの可能性がある`,
      "終了コードが 0 になる / 配列の添字がずれる",
    );
  }

  onStore(addr: number, _width: number, line: number): void {
    if (!inStack(addr)) return;
    const sp = Number(this.host.get(SP));
    if (addr < sp) {
      this.warn(
        "below-sp",
        line,
        `sp より下（0x${addr.toString(16)} < sp = 0x${sp.toString(16)}）へ書いている。` +
          `この領域は次の call がいつでも壊してよいことになっている`,
        "関数から戻ると壊れる（フレームサイズの計算違い）",
      );
      return;
    }
    const s0 = Number(this.host.get(S0));
    if (s0 !== 0 && addr >= s0) {
      this.warn(
        "caller-frame",
        line,
        `現在のフレームの外（0x${addr.toString(16)} >= s0 = 0x${s0.toString(16)}）へ書いている。` +
          `呼び出し元の領域を壊している可能性がある`,
        "関数から戻ると壊れる（フレームサイズの計算違い）",
      );
    }
  }

  /** main から戻るとき。終了コードは 0〜255 に丸められる */
  onMainReturn(raw: bigint, line: number): void {
    if (raw < 0n || raw > 255n) {
      this.warn(
        "exit-range",
        line,
        `main が ${raw} を返したが、終了コードは下位 8bit だけが残るので ` +
          `${Number(BigInt.asUintN(8, raw))} になる`,
        "期待値と 256 ずれる（終了コードは 0〜255）",
      );
    }
  }
}
