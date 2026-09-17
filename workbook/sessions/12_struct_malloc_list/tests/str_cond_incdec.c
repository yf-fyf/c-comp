// コマ11からの回帰: 条件式と前置 ++/-- の内側にある文字列も収集する。
#include "lib.h"

int main() {
    int n;
    int *p;

    n = 1;
    p = &n;
    printf(n < 2 ? "then\n" : "else\n");

    ++p["x"[0] - 'x'];
    printf(n < 2 ? "small\n" : "big\n");
    --p["y"[0] - 'y'];
    return n;
}
