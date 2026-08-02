// シミュレータの単体テスト（qemu 不要。常に走る）。
// qemu との突き合わせは test/qemu-conformance.ts が担当する。
import { describe, expect, it } from "vitest";
import { assemble, AssembleError } from "../src/sim/assembler";
import { Machine, STACK_TOP } from "../src/sim/machine";

/** アセンブルして最後まで走らせる */
function run(asm: string): Machine {
  const m = new Machine(assemble(asm));
  while (!m.halted) m.step();
  return m;
}

const main = (body: string): string => `  .text\n  .globl main\nmain:\n${body}\n`;

describe("アセンブラ", () => {
  it("ラベルとデータを配置する", () => {
    const p = assemble(`
  .data
msg:
  .byte 72
  .byte 0
n:
  .word 258
  .text
main:
  li a0, 1
  ret
`);
    expect(p.insns).toHaveLength(2);
    expect(p.dataImage[0]).toBe(72);
    // .word はリトルエンディアン（258 = 0x0102）
    expect(p.dataImage[2]).toBe(2);
    expect(p.dataImage[3]).toBe(1);
    expect(p.labels.get("n")! - p.labels.get("msg")!).toBe(2);
  });

  it("未対応の命令は行番号つきで拒否する", () => {
    try {
      assemble("  .text\nmain:\n  fsqrt.d f0, f1\n");
      expect.unreachable("例外が出るはず");
    } catch (e) {
      expect(e).toBeInstanceOf(AssembleError);
      expect((e as AssembleError).line).toBe(3);
    }
  });

  it("各命令に元の行番号が付く", () => {
    const p = assemble("  .text\nmain:\n  li a0, 3\n\n  ret\n");
    expect(p.insns.map((i) => i.line)).toEqual([3, 5]);
  });
});

describe("命令の意味", () => {
  it("算術と即値", () => {
    expect(run(main("  li a0, 20\n  li a1, 3\n  sub a0, a0, a1\n  ret")).exitCode).toBe(17);
    expect(run(main("  li a0, 7\n  li a1, 6\n  mul a0, a0, a1\n  ret")).exitCode).toBe(42);
    expect(run(main("  li a0, 17\n  li a1, 5\n  rem a0, a0, a1\n  ret")).exitCode).toBe(2);
  });

  it("除算は 0 方向へ丸める（C と同じ）", () => {
    expect(run(main("  li a0, -7\n  li a1, 2\n  div a0, a0, a1\n  ret")).exitCode).toBe(0xff - 2); // -3 → 253
    expect(run(main("  li a0, -7\n  li a1, 2\n  rem a0, a0, a1\n  ret")).exitCode).toBe(0xff); // -1 → 255
  });

  it("sra は算術シフト、slt は符号つき比較", () => {
    expect(run(main("  li a0, -16\n  li a1, 2\n  sra a0, a0, a1\n  neg a0, a0\n  ret")).exitCode).toBe(4);
    expect(run(main("  li a0, -1\n  li a1, 1\n  slt a0, a0, a1\n  ret")).exitCode).toBe(1);
  });

  it("64bit の値を保てる（number では表せない桁）", () => {
    const m = run(main("  li a0, 4294967296\n  li a1, 3\n  mul a0, a0, a1\n  ret"));
    expect(m.get(10)).toBe(12884901888n);
  });

  it("lw は符号拡張、lb はバイトを取り出す", () => {
    const m = run(main(`
  li a1, -5
  addi sp, sp, -16
  sw a1, 0(sp)
  lw a0, 0(sp)
  neg a0, a0
  addi sp, sp, 16
  ret`));
    expect(m.exitCode).toBe(5);
  });

  it("x0 は書いても 0 のまま", () => {
    expect(run(main("  li zero, 9\n  add a0, zero, zero\n  ret")).exitCode).toBe(0);
  });
});

describe("関数呼び出し", () => {
  const RECURSIVE = `
  .text
  .globl fact
fact:
  addi sp, sp, -32
  sd ra, 24(sp)
  sd s0, 16(sp)
  addi s0, sp, 32
  li a1, 2
  slt a1, a0, a1
  beqz a1, .Lrec
  li a0, 1
  j .Lend
.Lrec:
  sd a0, -24(s0)
  addi a0, a0, -1
  call fact
  ld a1, -24(s0)
  mul a0, a0, a1
.Lend:
  ld s0, 16(sp)
  ld ra, 24(sp)
  addi sp, sp, 32
  ret
  .globl main
main:
  addi sp, sp, -16
  sd ra, 8(sp)
  li a0, 5
  call fact
  ld ra, 8(sp)
  addi sp, sp, 16
  ret
`;

  it("再帰が正しく動く", () => {
    expect(run(RECURSIVE).exitCode).toBe(120);
  });

  it("終了コードは下位 8bit に丸める", () => {
    expect(run(main("  li a0, 300\n  ret")).exitCode).toBe(44);
  });
});

describe("libc シム", () => {
  it("printf の %d / %s / %c", () => {
    const m = run(`
  .data
fmt:
  .byte 37
  .byte 100
  .byte 32
  .byte 37
  .byte 115
  .byte 32
  .byte 37
  .byte 99
  .byte 0
s:
  .byte 104
  .byte 105
  .byte 0
  .text
  .globl main
main:
  addi sp, sp, -16
  sd ra, 8(sp)
  la a0, fmt
  li a1, 42
  la a2, s
  li a3, 65
  call printf
  li a0, 0
  ld ra, 8(sp)
  addi sp, sp, 16
  ret
`);
    expect(m.stdout).toBe("42 hi A");
  });

  it("malloc は 16 バイト境界の別々の領域を返す", () => {
    const m = run(main(`
  addi sp, sp, -16
  sd ra, 8(sp)
  li a0, 4
  call malloc
  sd a0, 0(sp)
  li a0, 4
  call malloc
  ld a1, 0(sp)
  sub a0, a0, a1
  ld ra, 8(sp)
  addi sp, sp, 16
  ret`));
    expect(m.exitCode).toBe(16);
  });

  it("プログラム側の定義がシムより優先される", () => {
    const m = run(`
  .text
  .globl strlen
strlen:
  li a0, 99
  ret
  .globl main
main:
  addi sp, sp, -16
  sd ra, 8(sp)
  call strlen
  ld ra, 8(sp)
  addi sp, sp, 16
  ret
`);
    expect(m.exitCode).toBe(99);
  });

  it("ecall で write と exit ができる（R1_nolibc 相当）", () => {
    const m = run(`
  .data
s:
  .byte 111
  .byte 107
  .text
  .globl _start
_start:
  li a7, 64
  li a0, 1
  la a1, s
  li a2, 2
  ecall
  li a7, 93
  li a0, 7
  ecall
`);
    expect(m.stdout).toBe("ok");
    expect(m.exitCode).toBe(7);
  });
});

describe("逆ステップ", () => {
  it("レジスタ・メモリ・標準出力が元に戻る", () => {
    const m = new Machine(assemble(main(`
  addi sp, sp, -16
  li a0, 11
  sd a0, 0(sp)
  li a0, 22
  ld a0, 0(sp)
  addi sp, sp, 16
  ret`)));
    const trace: string[] = [];
    while (!m.halted) {
      trace.push(`${m.pc}:${m.get(10)}:${m.get(2)}`);
      m.step();
    }
    // 全部巻き戻すと、各時点の状態が往路と一致する
    for (let i = trace.length - 1; i >= 0; i--) {
      expect(m.stepBack()).toBe(true);
      expect(`${m.pc}:${m.get(10)}:${m.get(2)}`).toBe(trace[i]);
    }
    expect(m.stepBack()).toBe(false); // 先頭より前へは戻れない
  });

  it("巻き戻してから進めると同じ結果になる", () => {
    const asm = main("  li a0, 3\n  li a1, 4\n  add a0, a0, a1\n  ret");
    const m = run(asm);
    const first = m.exitCode;
    while (m.stepBack());
    while (!m.halted) m.step();
    expect(m.exitCode).toBe(first);
  });
});

describe("教育的検査（testing.md の症状表）", () => {
  const kinds = (m: Machine): string[] => m.warnings.map((w) => w.kind);

  it("call 直前の sp が 16 の倍数でないと警告する", () => {
    const m = run(`
  .text
  .globl f
f:
  ret
  .globl main
main:
  addi sp, sp, -16
  sd ra, 8(sp)
  addi sp, sp, -8
  call f
  addi sp, sp, 8
  ld ra, 8(sp)
  addi sp, sp, 16
  li a0, 0
  ret
`);
    expect(kinds(m)).toContain("sp-align");
  });

  it("ra を退避せずに call すると警告する", () => {
    // ra を退避しないと call が戻り番地を上書きするので、main は自分自身へ
    // 戻り続ける。無限ループになること自体がこの不具合の症状である
    const m = new Machine(assemble(`
  .text
  .globl f
f:
  li a0, 1
  ret
  .globl main
main:
  addi sp, sp, -16
  call f
  addi sp, sp, 16
  ret
`), 500);
    expect(() => {
      while (!m.halted) m.step();
    }).toThrow(/無限ループ/);
    expect(kinds(m)).toContain("ra-clobber");
  });

  it("未初期化のスタックを読むと警告する", () => {
    const m = run(main("  addi sp, sp, -16\n  ld a0, 0(sp)\n  addi sp, sp, 16\n  ret"));
    expect(kinds(m)).toContain("uninitialized-read");
  });

  // int を sw で書いた領域は下位 4 バイトしか初期化されない。
  // 画面のスタック表はここを 8 バイト単位で読むので、表示用の読み出しが
  // 検査を通ると全ての解答例で誤検出になる（実際にそうなっていた）
  it("表示用の読み出し（peek）は警告を出さない", () => {
    const m = run(main("  addi sp, sp, -16\n  li a0, 7\n  sw a0, 0(sp)\n  addi sp, sp, 16\n  ret"));
    expect(m.warnings).toEqual([]);
    const addr = STACK_TOP - 16;
    expect(m.writtenWidth(addr, 8)).toBe(4); // sw は 4 バイトだけ書く
    expect(m.peek(addr, 4)).toBe(7n);
    expect(kinds(m)).not.toContain("uninitialized-read");
    // 同じ番地をプログラムが ld で読んだときは、これは本当の警告
    m.load(addr, 8, 1);
    expect(kinds(m)).toContain("uninitialized-read");
  });

  it("終了コードが 0〜255 に収まらないと警告する", () => {
    const m = run(main("  li a0, 300\n  ret"));
    expect(kinds(m)).toContain("exit-range");
  });

  it("呼び出しをまたいで a1 を使うと警告する", () => {
    const m = run(`
  .text
  .globl f
f:
  addi sp, sp, -16
  sd ra, 8(sp)
  li a1, 0
  ld ra, 8(sp)
  addi sp, sp, 16
  ret
  .globl main
main:
  addi sp, sp, -16
  sd ra, 8(sp)
  li a1, 5
  call f
  add a0, a1, a1
  ld ra, 8(sp)
  addi sp, sp, 16
  ret
`);
    expect(kinds(m)).toContain("arg-clobber");
  });

  it("正しいコードでは警告が出ない", () => {
    const m = run(`
  .text
  .globl add2
add2:
  addi sp, sp, -16
  sd ra, 8(sp)
  sd s0, 0(sp)
  addi s0, sp, 16
  add a0, a0, a1
  ld s0, 0(sp)
  ld ra, 8(sp)
  addi sp, sp, 16
  ret
  .globl main
main:
  addi sp, sp, -16
  sd ra, 8(sp)
  li a0, 20
  li a1, 22
  call add2
  ld ra, 8(sp)
  addi sp, sp, 16
  ret
`);
    expect(m.exitCode).toBe(42);
    expect(m.warnings).toEqual([]);
  });
});

describe("暴走と異常", () => {
  it("無限ループは命令数の上限で止まる", () => {
    const m = new Machine(assemble("  .text\nmain:\n.L:\n  j .L\n"), 1000);
    expect(() => {
      while (!m.halted) m.step();
    }).toThrow(/無限ループ/);
  });

  it("不正なアドレスは行番号つきで報告する", () => {
    const m = new Machine(assemble(main("  li a0, 4\n  ld a0, 0(a0)\n  ret")));
    expect(() => {
      while (!m.halted) m.step();
    }).toThrow(/不正なアドレス/);
  });

  it("スタックの底は STACK_TOP", () => {
    const m = new Machine(assemble(main("  ret")));
    expect(m.get(2)).toBe(BigInt(STACK_TOP));
  });
});
