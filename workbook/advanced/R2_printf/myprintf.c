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
// 1文字でも配列に入れてから渡す。
int print_char(int c) {
    char buf[1];
    // TODO(Step 1): buf[0] に c を入れて sys_write(1, buf, 1) する
    return 0;
}

// ---- Step 1: NUL 終端文字列を書く ----
int print_str(char *s) {
    // TODO(Step 1): my_strlen で長さを求めて sys_write(1, s, 長さ) する
    return 0;
}

// ---- Step 2: 整数を10進で書く ----
//
// 方針(下の桁から作って、逆から埋める):
//   1. 負数なら符号を覚えて正にする
//   2. バッファの末尾に NUL を置く
//   3. n % 10 で下の桁を取り、'0'(48) を足して文字にし、
//      バッファの手前へ詰める。n = n / 10 で次の桁へ
//   4. n == 0 のときは '0' を1文字だけ出す(ループが1度も回らないため)
//   5. 負数なら '-'(45) を先頭に足す
//   6. 詰め始めた位置 &buf[i] から print_str する
//
// 文字コード: '0' = 48、'-' = 45
int print_int(int n) {
    char buf[16];
    int i;
    int neg;
    // TODO(Step 2)
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
