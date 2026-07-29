// RV64 の実行機械。
//
// 値は 64bit なので BigInt64Array で持つ（JS の number では表せない）。
// アドレスは number で扱い、メモリアクセスの直前だけ Number() に落とす。
//
// step() は1命令だけ進め、変わった分の「元の値」を取り消しログに積む。
// 逆ステップはそれを巻き戻すだけなので、全状態のスナップショットは持たない。

import { TEXT_BASE, textIndex, type Insn, type Program } from "./assembler";
import { callShim, isShimName } from "./libc";
import { Checker, type Warning } from "./checks";

export const DATA_BASE = 0x00100000;
export const HEAP_BASE = 0x00200000;
export const STACK_LOW = 0x00300000;
export const STACK_TOP = 0x00400000;
const MEM_END = STACK_TOP;
const MEM_SIZE = MEM_END - DATA_BASE;

/** main から戻ったことを表す番兵。実在しないアドレスにする */
export const RETURN_SENTINEL = 0xdead0000;

export const REG = {
  zero: 0, ra: 1, sp: 2, s0: 8, a0: 10, a1: 11, a7: 17,
} as const;

export interface MemUndo {
  addr: number;
  bytes: Uint8Array;
  init: Uint8Array;
}

export interface Undo {
  pc: number;
  regs: { index: number; value: bigint }[];
  mem: MemUndo[];
  stdoutLength: number;
  heapTop: number;
  warningCount: number;
  halted: boolean;
  exitCode: number | null;
  checker: unknown;
}

export interface StepOutcome {
  /** 実行した命令。プログラム終了後は null */
  insn: Insn | null;
  halted: boolean;
  /** このステップで出た警告 */
  warnings: Warning[];
}

export class MachineError extends Error {
  constructor(message: string, readonly line: number) {
    super(message);
  }
}

export class Machine {
  readonly regs = new BigInt64Array(32);
  readonly mem = new Uint8Array(MEM_SIZE);
  /** バイトごとの「書かれたことがあるか」。未初期化読み出しの検出に使う */
  readonly init = new Uint8Array(MEM_SIZE);
  pc = 0;
  halted = false;
  exitCode: number | null = null;
  stdout = "";
  heapTop = HEAP_BASE;
  steps = 0;
  readonly warnings: Warning[] = [];
  readonly undoLog: Undo[] = [];
  /** 現在のステップで積む取り消し情報 */
  private pending: Undo | null = null;
  // set() から参照するので、コンストラクタの途中では未定義になりうる
  private readonly checker!: Checker;
  readonly entryName: string;

  constructor(readonly program: Program, readonly maxSteps = 1_000_000) {
    // データ・bss の初期像を置く（この領域は初期化済みとして扱う）
    this.mem.set(program.dataImage, DATA_BASE - DATA_BASE);
    this.init.fill(1, 0, program.dataImage.length);
    // ヒープ領域も 0 初期化済みとみなす（malloc の戻り先）
    this.init.fill(1, HEAP_BASE - DATA_BASE, STACK_LOW - DATA_BASE);

    const entry = program.textLabels.has("_start") ? "_start" : "main";
    const entryAddr = program.textLabels.get(entry);
    if (entryAddr === undefined) {
      throw new MachineError(`エントリポイントがない（main も _start も見つからない）`, 0);
    }
    this.entryName = entry;
    this.pc = entryAddr;
    this.regs[REG.sp] = BigInt(STACK_TOP);
    this.regs[REG.s0] = BigInt(STACK_TOP);
    this.regs[REG.ra] = BigInt(RETURN_SENTINEL);
    this.checker = new Checker(this);
    this.checker.enterEntry(entry, STACK_TOP);
  }

  // ── レジスタ ──

  get(index: number): bigint {
    return this.regs[index]!;
  }

  set(index: number, value: bigint): void {
    if (index === 0) return; // x0 は常に 0
    this.pending?.regs.push({ index, value: this.regs[index]! });
    this.regs[index] = value;
    this.checker?.onRegWrite(index);
  }

  // ── メモリ ──

  private checkRange(addr: number, width: number, line: number): number {
    const off = addr - DATA_BASE;
    if (off < 0 || off + width > MEM_SIZE) {
      throw new MachineError(
        `不正なアドレスへのアクセス: 0x${(addr >>> 0).toString(16)}` +
          `（未初期化のポインタか、配列の範囲外の可能性）`,
        line,
      );
    }
    return off;
  }

  /**
   * 表示のための読み出し。検査器を通さないので警告を出さない。
   * 画面の描画はプログラムの動作ではないので、こちらを使うこと。
   */
  peek(addr: number, width: 1 | 4 | 8): bigint {
    const off = addr - DATA_BASE;
    if (off < 0 || off + width > MEM_SIZE) return 0n;
    let value = 0n;
    for (let i = width - 1; i >= 0; i--) value = (value << 8n) | BigInt(this.mem[off + i]!);
    return BigInt.asIntN(width * 8, value); // lb / lw は符号拡張
  }

  /** addr から連続して何バイトが書き込み済みか（表示用。int は 4、char は 1 になる） */
  writtenWidth(addr: number, width: number): number {
    const off = addr - DATA_BASE;
    if (off < 0 || off + width > MEM_SIZE) return 0;
    let n = 0;
    while (n < width && this.init[off + n] === 1) n++;
    return n;
  }

  load(addr: number, width: 1 | 4 | 8, line: number): bigint {
    const off = this.checkRange(addr, width, line);
    for (let i = 0; i < width; i++) {
      if (this.init[off + i] === 0) {
        this.checker.onUninitializedRead(addr, width, line);
        break;
      }
    }
    return this.peek(addr, width);
  }

  store(addr: number, width: 1 | 4 | 8, value: bigint, line: number): void {
    const off = this.checkRange(addr, width, line);
    if (this.pending) {
      this.pending.mem.push({
        addr,
        bytes: this.mem.slice(off, off + width),
        init: this.init.slice(off, off + width),
      });
    }
    let v = BigInt.asUintN(width * 8, value);
    for (let i = 0; i < width; i++) {
      this.mem[off + i] = Number(v & 0xffn);
      this.init[off + i] = 1;
      v >>= 8n;
    }
    this.checker.onStore(addr, width, line);
  }

  readCString(addr: number): string {
    let s = "";
    for (let a = addr; a < MEM_END; a++) {
      const off = a - DATA_BASE;
      if (off < 0 || off >= MEM_SIZE) break;
      const b = this.mem[off]!;
      if (b === 0) return s;
      s += String.fromCharCode(b);
    }
    return s;
  }

  malloc(size: number): number {
    const addr = this.heapTop;
    this.heapTop = (this.heapTop + Math.max(size, 1) + 15) & ~15; // 16 バイト境界
    if (this.heapTop > STACK_LOW) throw new MachineError("ヒープを使い切った", 0);
    return addr;
  }

  write(text: string): void {
    this.stdout += text;
  }

  exit(code: number): void {
    this.halted = true;
    this.exitCode = code & 0xff; // qemu と同じく下位 8bit
  }

  addWarning(w: Warning): void {
    this.warnings.push(w);
  }

  // ── 実行 ──

  currentInsn(): Insn | null {
    if (this.halted) return null;
    const index = textIndex(this.pc);
    return this.program.insns[index] ?? null;
  }

  step(): StepOutcome {
    if (this.halted) return { insn: null, halted: true, warnings: [] };
    if (this.steps >= this.maxSteps) {
      this.halted = true;
      throw new MachineError(
        `${this.maxSteps} 命令を超えた（無限ループの可能性）。` +
          `ループの終了条件と、カウンタの更新が同じ変数を指しているかを確かめる`,
        this.currentInsn()?.line ?? 0,
      );
    }
    const insn = this.currentInsn();
    if (insn === null) {
      throw new MachineError(
        `プログラムの外へ飛んだ（pc = 0x${this.pc.toString(16)}）。` +
          `ret の前に ra が壊れていないか確かめる`,
        0,
      );
    }

    const undo: Undo = {
      pc: this.pc,
      regs: [],
      mem: [],
      stdoutLength: this.stdout.length,
      heapTop: this.heapTop,
      warningCount: this.warnings.length,
      halted: this.halted,
      exitCode: this.exitCode,
      checker: this.checker.snapshot(),
    };
    this.pending = undo;
    const warningBase = this.warnings.length;

    try {
      this.checker.beforeExecute(insn);
      this.execute(insn);
    } finally {
      this.pending = null;
    }
    this.undoLog.push(undo);
    this.steps++;

    return {
      insn,
      halted: this.halted,
      warnings: this.warnings.slice(warningBase),
    };
  }

  stepBack(): boolean {
    const undo = this.undoLog.pop();
    if (!undo) return false;
    for (let i = undo.regs.length - 1; i >= 0; i--) {
      const r = undo.regs[i]!;
      this.regs[r.index] = r.value;
    }
    for (let i = undo.mem.length - 1; i >= 0; i--) {
      const m = undo.mem[i]!;
      const off = m.addr - DATA_BASE;
      this.mem.set(m.bytes, off);
      this.init.set(m.init, off);
    }
    this.pc = undo.pc;
    this.stdout = this.stdout.slice(0, undo.stdoutLength);
    this.heapTop = undo.heapTop;
    this.warnings.length = undo.warningCount;
    this.halted = undo.halted;
    this.exitCode = undo.exitCode;
    this.checker.restore(undo.checker);
    this.steps--;
    return true;
  }

  private execute(insn: Insn): void {
    const next = this.pc + 4;
    const rs1 = this.get(insn.rs1);
    const rs2 = this.get(insn.rs2);
    const line = insn.line;

    switch (insn.op) {
      // 算術（レジスタ3つ）
      case "add": this.set(insn.rd, rs1 + rs2); break;
      case "sub": this.set(insn.rd, rs1 - rs2); break;
      case "mul": this.set(insn.rd, rs1 * rs2); break;
      case "div":
        if (rs2 === 0n) throw new MachineError("0 で除算した", line);
        this.set(insn.rd, rs1 / rs2); // BigInt の除算は 0 方向へ丸める（C と同じ）
        break;
      case "rem":
        if (rs2 === 0n) throw new MachineError("0 で剰余を取った", line);
        this.set(insn.rd, rs1 % rs2);
        break;
      case "and": this.set(insn.rd, rs1 & rs2); break;
      case "or": this.set(insn.rd, rs1 | rs2); break;
      case "xor": this.set(insn.rd, rs1 ^ rs2); break;
      case "sll": this.set(insn.rd, rs1 << (rs2 & 63n)); break;
      case "sra": this.set(insn.rd, rs1 >> (rs2 & 63n)); break;
      case "slt": this.set(insn.rd, rs1 < rs2 ? 1n : 0n); break;

      // 即値
      case "addi": this.set(insn.rd, rs1 + insn.imm); break;
      case "xori": this.set(insn.rd, rs1 ^ insn.imm); break;
      case "li": this.set(insn.rd, insn.imm); break;
      case "la": this.set(insn.rd, BigInt(insn.offset)); break;

      // 単項
      case "mv": this.set(insn.rd, rs1); break;
      case "neg": this.set(insn.rd, -rs1); break;
      case "not": this.set(insn.rd, ~rs1); break;
      case "seqz": this.set(insn.rd, rs1 === 0n ? 1n : 0n); break;
      case "snez": this.set(insn.rd, rs1 !== 0n ? 1n : 0n); break;

      // メモリ
      case "lb": this.set(insn.rd, this.load(Number(rs1) + insn.offset, 1, line)); break;
      case "lw": this.set(insn.rd, this.load(Number(rs1) + insn.offset, 4, line)); break;
      case "ld": this.set(insn.rd, this.load(Number(rs1) + insn.offset, 8, line)); break;
      case "sb": case "sw": case "sd": {
        const width = insn.op === "sb" ? 1 : insn.op === "sw" ? 4 : 8;
        this.checker.onStoreReg(insn.rd);
        this.store(Number(rs1) + insn.offset, width as 1 | 4 | 8, this.get(insn.rd), line);
        break;
      }

      // 分岐
      case "beqz":
        this.pc = rs1 === 0n ? insn.offset : next;
        return;
      case "bnez":
        this.pc = rs1 !== 0n ? insn.offset : next;
        return;
      case "j":
        this.pc = insn.offset;
        return;

      case "call":
      case "jal": {
        const name = insn.target!;
        this.checker.onCall(name, insn);
        if (!this.program.textLabels.has(name)) {
          if (!isShimName(name)) {
            throw new MachineError(
              `未定義の関数を呼んでいる: '${name}'`, line,
            );
          }
          callShim(name, this);
          this.checker.onReturn(); // onCall で積んだフレームを戻す
          this.pc = next;
          return;
        }
        this.set(REG.ra, BigInt(next));
        this.pc = this.program.textLabels.get(name)!;
        return;
      }

      case "ret": {
        const target = Number(BigInt.asUintN(32, this.get(REG.ra)));
        this.checker.onReturn();
        if (target === RETURN_SENTINEL) {
          const raw = BigInt.asIntN(32, this.get(REG.a0));
          this.checker.onMainReturn(raw, line);
          this.exit(Number(raw));
          this.pc = next;
          return;
        }
        this.pc = target;
        return;
      }

      case "ecall": {
        const which = this.get(REG.a7);
        if (which === 64n) {
          // write(fd, buf, len)
          const buf = Number(this.get(REG.a1));
          const len = Number(this.get(12)); // a2
          let s = "";
          for (let i = 0; i < len; i++) {
            s += String.fromCharCode(this.mem[buf + i - DATA_BASE] ?? 0);
          }
          this.write(s);
          this.set(REG.a0, BigInt(len));
        } else if (which === 93n) {
          this.exit(Number(BigInt.asIntN(32, this.get(REG.a0))));
        } else {
          throw new MachineError(`未対応のシステムコール番号: ${which}`, line);
        }
        this.pc = next;
        return;
      }

      default:
        throw new MachineError(`未実装の命令: '${insn.op}'`, line);
    }
    this.pc = next;
  }
}

/** 停止するまで走らせる。UI を固めないよう呼び出し側で分割して使う */
export function runToEnd(m: Machine, limit = Infinity): void {
  let n = 0;
  while (!m.halted && n < limit) {
    m.step();
    n++;
  }
}
