// OCaml コア（web/core/js/api.ml）が返す JSON に対応する型定義。
// AST本体のキー名・省略規則は scaffold/parse_viewer.py の node_to_dict と同じ。
// sourceRanges だけはエディタ連携用のWeb固有メタデータ。
// スキーマの二重管理を避けるため、実行時検査は test/core.test.ts の1本で行う。

export interface AstNode {
  kind: string;
  lhs?: AstNode;
  rhs?: AstNode;
  cond?: AstNode;
  then?: AstNode;
  else_?: AstNode;
  init?: AstNode;
  step?: AstNode;
  body?: AstNode;
  operand?: AstNode;
  stmts?: AstNode[];
  args?: AstNode[];
  params?: AstNode[];
  val?: number;
  sval?: string;
  name?: string;
  ty_str?: string;
  type_sexp?: string;
  init_expr?: AstNode;
  is_arrow?: boolean;
  line?: number; // 前処理後の行番号。エディタ行へは lineMap で写す
  sourceRanges?: SourceRange[]; // 元ソース上のUTF-16半開区間
}

export interface SourceRange {
  from: number;
  to: number;
}

export interface Token {
  kind: "TK_NUM" | "TK_CHAR" | "TK_STR" | "TK_IDENT" | "TK_KW" | "TK_PUNCT" | "TK_EOF";
  text: string;
  val?: number;
  line: number;
}

export interface ParseError {
  message: string;
  line: number; // 前処理後の行番号。0 = 不明
  col?: number; // 行頭からの UTF-8 バイト数（1 起点）。0 = 不明。compile のみが付与する
  phase?: "preprocess" | "parse" | "typing"; // compile のみが付与する
}

export interface ParseResult {
  ok: boolean;
  tokens?: Token[];
  ast?: AstNode[];
  lineMap?: [number, number][]; // [前処理後の行, 元ソースの行]
  errors?: ParseError[];
}

export interface TextResult {
  ok: boolean;
  text?: string;
  errors?: ParseError[];
}

/** 文 1 つと、その文が出した命令の範囲（A3 のクロスハイライト用） */
export interface StmtSpan {
  sourceRanges: SourceRange[]; // 元ソース上のUTF-16半開区間（AstNode と同じ土俵）
  fromLine: number; // 出力アセンブリの行番号（1 起点の閉区間）
  toLine: number;
}

/** compile の戻り値。text に加えて文と命令の対応表を持つ */
export interface CompileResult extends TextResult {
  stmtMap?: StmtSpan[];
}

export interface ExampleItem {
  label: string;
  path: string;
  source: string;
}

export interface ExampleGroup {
  group: string;
  items: ExampleItem[];
}
