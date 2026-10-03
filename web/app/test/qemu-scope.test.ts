import { expect, it } from "vitest";
import { assemble } from "../src/sim/assembler";
import { conformanceExclusion } from "./qemu-scope";

it("未対応のストリーム関数を理由つきで除外する", () => {
  const program = assemble(".text\nmain:\n call fdopen\n call fclose\n call fdopen\n ret\n");
  expect(conformanceExclusion(program)).toBe("未対応のストリームI/O: fclose, fdopen");
});

it("プログラム自身が定義した同名の関数は検査する", () => {
  const program = assemble(".text\nfdopen:\n ret\nmain:\n call fdopen\n ret\n");
  expect(conformanceExclusion(program)).toBeNull();
});

it("他の未知の呼び出しを対象外として隠さない", () => {
  const program = assemble(".text\nmain:\n call unknown_function\n ret\n");
  expect(conformanceExclusion(program)).toBeNull();
});
