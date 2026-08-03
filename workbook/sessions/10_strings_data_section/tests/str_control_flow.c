// 文の走査 — if / else / while / for の中だけに置いた文字列リテラルを集められるか。
// else 節は実行されないが、.data に出ていないとラベルが未定義でリンクできない。
#include "lib.h"

int main() {
    int i;

    if (1) {
        printf("in if\n");
    } else {
        printf("in else\n");
    }

    i = 0;
    while (i < 2) {
        printf("in while\n");
        i = i + 1;
    }

    for (i = 0; i < 2; i = i + 1) {
        printf("in for\n");
    }

    return 0;
}
