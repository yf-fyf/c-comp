// 三項演算子の走査 — 選ばれなかった側の枝にある文字列も .data に出す必要がある。
#include "lib.h"

int main() {
    int n;
    char *s;

    n = 3;
    s = n < 2 ? "small" : "big";
    printf("%s\n", s);

    printf("%s\n", n < 2 ? "then side" : "else side");
    return 0;
}
