// 型対応の前置 ++ / -- 単体 — int * は 4 バイト、char * は 1 バイト、int は 1 だけ動くか
// （実装手順 8 の直後に通る）。
#include "lib.h"

int main() {
    int *a;
    int *p;
    char *s;
    char *t;
    int n;
    a = malloc(sizeof(int) * 3);
    a[0] = 5;
    a[1] = 6;
    a[2] = 7;
    p = a;
    ++p;
    if (*p != 6) {
        return 1;
    }
    ++p;
    if (*p != 7) {
        return 2;
    }
    --p;
    if (*p != 6) {
        return 3;
    }
    s = malloc(2);
    s[0] = 'a';
    s[1] = 'b';
    t = s;
    ++t;
    if (*t != 'b') {
        return 4;
    }
    --t;
    if (*t != 'a') {
        return 5;
    }
    n = 10;
    ++n;
    --n;
    --n;
    if (n != 9) {
        return 6;
    }
    ++t;
    return *p + *t;
}
