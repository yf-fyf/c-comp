// 両アプリで共通の外枠。アプリ間のナビゲーションと文字サイズ切替。
// 文字サイズは授業中の教員デモ要件（design/webapps.md 1章）。

const FONT_KEY = "mycc-font-size";

export interface AppLink {
  href: string;
  label: string;
}

export const APPS: AppLink[] = [
  { href: "./index.html", label: "ツール一覧" },
  { href: "./ast.html", label: "AST ビジュアライザ" },
  { href: "./compile.html", label: "C コンパイラ" },
  { href: "./sim.html", label: "RV64 シミュレータ" },
];

/** ヘッダの共通部分（ナビ・文字サイズ）を組み立てる */
export function mountShell(currentHref: string): void {
  applyFont(localStorage.getItem(FONT_KEY) ?? "m");

  const nav = document.getElementById("app-nav");
  if (nav) {
    for (const app of APPS) {
      const a = document.createElement("a");
      a.href = app.href;
      a.textContent = app.label;
      if (app.href.endsWith(currentHref)) a.className = "current";
      nav.appendChild(a);
    }
  }

  const buttons = document.getElementById("font-buttons");
  if (buttons) {
    for (const btn of buttons.querySelectorAll<HTMLButtonElement>("button")) {
      btn.addEventListener("click", () => {
        const size = btn.dataset.size ?? "m";
        applyFont(size);
        localStorage.setItem(FONT_KEY, size);
      });
    }
  }
}

function applyFont(size: string): void {
  document.documentElement.dataset.font = size;
  for (const btn of document.querySelectorAll<HTMLButtonElement>("#font-buttons button")) {
    btn.classList.toggle("active", btn.dataset.size === size);
  }
}

/** 要素を id で引く。無ければ例外（取り違えを早く見つけるため） */
export function el<T extends HTMLElement>(id: string): T {
  const e = document.getElementById(id);
  if (!e) throw new Error(`要素がない: #${id}`);
  return e as T;
}
