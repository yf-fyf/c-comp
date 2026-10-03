#include "lib.h"

int *identity(int *p) {
    return p;
}

int **identity_ptr(int **p) {
    return p;
}

int main() {
    int *p;
    p = malloc(sizeof(int) * 3);
    p[0] = 0;
    p[1] = 19;
    p[2] = 23;
    // 呼出し結果も int *。+1/-1 は4バイトぶん移動する。
    if (*(identity(p) + 1) != 19) return 1;
    if (*(identity(p + 2) - 1) != 19) return 2;
    // 多段ポインタを返す呼出しでは、内側の * は8バイトで読む。
    if (**identity_ptr(&p) != 0) return 3;
    return identity(p)[2];
}
