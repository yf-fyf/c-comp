// f11: ポインタ演算 — malloc した領域を sizeof と添字・ポインタ走査で使う
#include "lib.h"

int sum(int *a, int n) {
    int i;
    int s;
    s = 0;
    for (i = 0; i < n; ++i) {
        s = s + *(a + i);
    }
    return s;
}

int main() {
    int *a;
    a = malloc(sizeof(int) * 5);
    a[0] = 10;
    a[1] = 20;
    a[2] = 30;
    a[3] = 5;
    a[4] = 7;
    return sum(a, 5);
}
