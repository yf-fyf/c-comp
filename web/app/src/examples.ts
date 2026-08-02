// C のプリセット（workbook/**/tests/*.c から tools/build_web_examples.py が生成）。
// もとは ast-main.ts / compile-main.ts に同じ読み込みが重複していたが、
// T138 で旧3ページを削除したので、現在の読み込み口はここだけである。
import type { ExampleGroup, ExampleItem } from "./types";

/**
 * examples.json を読んで select に optgroup を組み立てる。
 * 返すのは path → 項目の対応表。読めなければ select を無効化して空の表を返す。
 * 選択時の動作と URL の書き換えは呼び出し側が受け持つ。
 */
export async function loadCExamples(
  select: HTMLSelectElement,
): Promise<Map<string, ExampleItem>> {
  let groups: ExampleGroup[] = [];
  try {
    const res = await fetch("examples.json");
    groups = (await res.json()) as ExampleGroup[];
  } catch {
    select.disabled = true;
    return new Map();
  }
  for (const g of groups) {
    const og = document.createElement("optgroup");
    og.label = g.group;
    for (const item of g.items) {
      const opt = document.createElement("option");
      opt.value = item.path;
      opt.textContent = item.label;
      og.appendChild(opt);
    }
    select.appendChild(og);
  }
  return new Map(groups.flatMap((g) => g.items.map((i) => [i.path, i] as const)));
}
