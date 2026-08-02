// 統合ページのアセンブリビュー（T137）。移植元は削除済みの compile-main.ts（git 履歴を参照）。
//
// 移植元との違いは3点だけ。
//  - 状態表示は #status ではなく #asm-status（#status は AST の解析結果が使う）
//  - 文書全体の Ctrl+Enter は「作る」モードのときだけ効かせる（動かすモードとの衝突回避）
//  - ［実行へ送る］で、コンパイル結果を動かすモードのバッファへ明示的に渡す
//
// 「作る」モードのアセンブリは明示操作でしか更新しない（T38 B6）。
// AST 側が自動更新なのと不揃いだが、これはモードの性格の違いとして注記に常掲する。
import { EditorView } from "codemirror";
import { compile, coreReady } from "./core";
import { el as $ } from "./shell";

// 自動コンパイルの設定は移植元と同じキーを引き継ぐ
const AUTO_KEY = "mycc-auto-compile";
const PLACEHOLDER =
  "ここに生成された RV64 アセンブリが出ます。\n［コンパイル］（Ctrl+Enter）を押してください。";

export interface AsmView {
  /** Mod-Enter キーマップから呼ぶ（app-main.ts がエディタ生成時に配線する） */
  runCompile(): void;
  /** コアの読み込みが済んでから初期表示を決める */
  start(): Promise<void>;
}

export interface AsmViewOptions {
  editor: EditorView;
  /** C ソースの変更を購読する（app-main.ts の docChangeListeners） */
  onSourceChange(f: () => void): void;
  /** 「作る」モードを表示中か（文書全体の Ctrl+Enter をモードでゲートする） */
  isActive(): boolean;
  /** ［実行へ送る］。動かすモードへアセンブリを渡し、モードも切り替える */
  sendToRun(text: string): void;
}

export function initAsmView(opts: AsmViewOptions): AsmView {
  const { editor } = opts;

  const autoBox = $<HTMLInputElement>("opt-auto");
  const button = $<HTMLButtonElement>("btn-compile");
  const sendButton = $<HTMLButtonElement>("btn-send-run");
  let auto = localStorage.getItem(AUTO_KEY) === "1";
  // 一度でもコンパイル結果を出したか。まだなら右ペインは案内文のまま
  let hasOutput = false;
  // ［実行へ送る］で渡す本文。直近の成功結果を持つ（stale 表示中でも送れる）
  let lastGoodAsm = "";
  let timer: ReturnType<typeof setTimeout> | undefined;

  function setStatus(cls: string, text: string): void {
    const status = $("asm-status");
    status.className = cls;
    status.textContent = text;
  }

  /** ソースまたはオプションが変わった。自動コンパイルが入なら走らせ、切なら「未反映」を示す */
  function markDirty(): void {
    if (auto) {
      clearTimeout(timer);
      timer = setTimeout(runCompile, 250);
      return;
    }
    clearTimeout(timer);
    button.classList.add("dirty");
    if (hasOutput) {
      // 表示中のアセンブリは今のソースの出力ではない、と分かるようにする
      $("asm-output").classList.add("stale");
      setStatus("pending", "● 変更あり — ［コンパイル］（Ctrl+Enter）で更新");
    } else {
      setStatus("pending", "［コンパイル］（Ctrl+Enter）でアセンブリを生成します");
    }
  }

  async function runCompile(): Promise<void> {
    clearTimeout(timer);
    button.classList.remove("dirty");
    const src = editor.state.doc.toString();
    const comments = $<HTMLInputElement>("opt-comments").checked;
    const result = await compile(src, comments);
    const out = $("asm-output");
    if (result.ok) {
      const text = result.text ?? "";
      out.textContent = text;
      out.classList.remove("stale", "placeholder");
      hasOutput = true;
      lastGoodAsm = text;
      sendButton.disabled = false;
      const lines = text === "" ? 0 : text.split("\n").length;
      setStatus("ok", `✓ コンパイル成功（${lines} 行）`);
    } else {
      // 直前の成功結果は消さずに薄く残す。入力途中の一時的なエラーで
      // 右ペインが点滅しないようにしつつ、古い出力だと分かるようにする。
      if (hasOutput) out.classList.add("stale");
      const err = result.errors?.[0];
      // line は前処理後の行番号（TextResult に行対応表は無い）。0 = 不明。
      // col は行頭からのバイト数（1 起点）で、取れないフェーズ（前処理）では 0 になる。
      let where = "";
      if (err && err.line) {
        where = err.col ? `（${err.line} 行 ${err.col} 桁）` : `（${err.line} 行目）`;
      }
      setStatus("err", `✗ ${err?.message ?? "エラー"}${where}`);
    }
  }

  button.addEventListener("click", runCompile);
  $("opt-comments").addEventListener("change", markDirty);

  autoBox.checked = auto;
  autoBox.addEventListener("change", () => {
    auto = autoBox.checked;
    localStorage.setItem(AUTO_KEY, auto ? "1" : "0");
    if (auto) runCompile();
  });

  // 送るのは直近の成功結果。stale 表示中でも「いま画面にある出力」と一致する
  sendButton.addEventListener("click", () => {
    if (!hasOutput) return;
    opts.sendToRun(lastGoodAsm);
  });

  // エディタ外（プリセット等）にフォーカスがあるときの Ctrl+Enter。
  // エディタ内は app-main.ts の keymap が処理し preventDefault 済みなので二重に走らせない。
  // 動かすモードでは無関係な操作なので、モードで止める。
  document.addEventListener("keydown", (e) => {
    if (!opts.isActive()) return;
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !e.defaultPrevented) {
      e.preventDefault();
      runCompile();
    }
  });

  opts.onSourceChange(markDirty);

  // 初期表示は案内文にする。読み込んだだけでアセンブリが出ていると
  // 「プログラムと出力を並べただけの表」に見え、コンパイルしている実感が出ないため。
  // 自動コンパイルを入にしている人だけ、その設定どおり読み込み時にも走る。
  $("asm-output").textContent = PLACEHOLDER;
  $("asm-output").classList.add("placeholder");
  sendButton.disabled = true;

  // コア初期化待ちの間はコンパイル操作を無効化する。
  button.disabled = true;
  setStatus("pending", "コアを読み込み中…");

  return {
    runCompile() {
      void runCompile();
    },
    async start(): Promise<void> {
      await coreReady();
      button.disabled = false;
      if (auto) await runCompile();
      else markDirty();
    },
  };
}
