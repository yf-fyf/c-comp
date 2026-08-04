// 教育的核心 — sizeof はオペランドを評価しない
//
// sizeof bump() の値は「bump() の戻り値の型のサイズ」であって、
// bump() を呼んで得た値ではない。数だけ見ると 4 で正しく見えるが、
// bump() が呼ばれてしまっていたら意味論として間違いである。
// 呼ばれたかどうかは calls を表示して確かめる。
#include "lib.h"

int calls;

int bump() {
    calls = calls + 1;
    return 7;
}

int main() {
    int n;
    int *p;

    calls = 0;
    n = sizeof bump();
    printf("sizeof bump(): calls=%d size=%d\n", calls, n);
    if (calls != 0) { return 1; }
    if (n != 4) { return 2; }

    // 比較のため、実際に呼ぶと calls は増える
    calls = 0;
    n = bump();
    printf("bump():        calls=%d ret=%d\n", calls, n);
    if (calls != 1) { return 3; }

    // 代入も ++ も、sizeof の中では起きない
    calls = 0;
    n = sizeof (calls = 99);
    printf("sizeof (calls = 99): calls=%d size=%d\n", calls, n);
    if (calls != 0) { return 4; }
    if (n != 4) { return 5; }

    calls = 0;
    n = sizeof ++calls;
    printf("sizeof ++calls: calls=%d size=%d\n", calls, n);
    if (calls != 0) { return 6; }
    if (n != 4) { return 7; }

    // 評価されないので、NULL の間接参照でも落ちない
    p = 0;
    n = sizeof *p;
    printf("sizeof *p:     n=%d\n", n);
    if (n != 4) { return 8; }

    return 42;
}
