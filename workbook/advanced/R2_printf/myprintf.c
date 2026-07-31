// R2: 自前 printf(スケルトン)
//
// libc を使わず、R1 の sys_write の上に出力機能を組み立てる。
// Core プロファイルでは可変長引数の「定義」ができないため、
// 引数が固定の関数を組み合わせる形にする。
//
// 実装する順番:
//   Step 1: my_strlen / print_char / print_str
//   Step 2: print_int
//   Step 3: printf1
//
// 確認:
//   python3 check.py

int sys_write(int fd, char *buf, int len);

// ---- Step 1: 文字列の長さ ----
// NUL(0)が出てくるまで数える。
int my_strlen(char *s) {
    return 0;   // TODO(Step 1)
}

// ---- Step 1: 1文字だけ書く ----
// sys_write は「バッファの先頭アドレス」と「バイト数」を要求するので、
// 1文字分の変数を用意し、そのアドレス &ch を渡す。
int print_char(int c) {
    char ch;
    // TODO(Step 1): ch に c を入れて sys_write(1, &ch, 1) する
    return 0;
}

// ---- Step 1: NUL 終端文字列を書く ----
int print_str(char *s) {
    // TODO(Step 1): my_strlen で長さを求めて sys_write(1, s, 長さ) する
    return 0;
}

// ---- Step 2: 整数を10進で書く ----
//
// 方針(上位桁を先に、再帰で出す):
//   1. 負数なら '-'(45) を print_char で出し、n = -n として以降は正の数を扱う
//   2. n が2桁以上(n >= 10)なら、上位の桁を先に print_int(n / 10) で出す
//   3. 最後に一の位 n % 10 に '0'(48) を足して print_char で出す
//
// n == 0 は 2. の条件が成り立たずそのまま 3. に落ちるので、
// 「0 を1文字だけ出す」特別扱いは不要になる。
//
// 文字コード: '0' = 48、'-' = 45
int print_int(int n) {
    // TODO(Step 2): 上の方針をそのまま if 文に落とす
    return 0;
}

// ---- Step 3: 書式つき出力(引数1個) ----
//
// %d = iarg を10進で、%s = sarg を文字列で、%c = iarg を1文字で、
// %% = '%' そのもの。それ以外の文字はそのまま出す。
//
// 方針: fmt を1文字ずつ見て、'%'(37) が来たら次の1文字で分岐する。
// 文字コード: '%' = 37、'd' = 100、's' = 115、'c' = 99
int printf1(char *fmt, int iarg, char *sarg) {
    int i;
    int n;
    // TODO(Step 3)
    return 0;
}
