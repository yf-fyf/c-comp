// 多段ポインタ — int ** の宣言、& と * の重ね掛け、ポインタ配列の尺度が 8 バイトであること
#include "lib.h"

int main() {
    int x;
    int *p;
    int **pp;
    int **q;
    x = 7;
    p = &x;
    pp = &p;
    **pp = **pp + 3;
    q = malloc(sizeof(int *) * 2);
    q[0] = p;
    q[1] = p;
    return *q[0] + *(*(q + 1));
}
