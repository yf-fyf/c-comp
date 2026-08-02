// _intern の重複排除 — 同じ内容の文字列リテラルは1つのラベルにまとめ、
// 内容が違う文字列には別のラベルを割り当てる。アドレスの一致・不一致で確かめる。
#include "lib.h"

int main() {
    char *a;
    char *b;
    char *c;

    a = "same";
    b = "same";
    c = "other";

    if (a != b) {
        return 1;
    }
    if (a == c) {
        return 2;
    }

    printf("%s\t%s\n", a, c);
    return 0;
}
