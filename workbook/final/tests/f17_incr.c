// f17: 前置インクリメント — int とポインタの両方を進める
#include "lib.h"

int main() {
    int i;
    int s;
    int *p;
    p = malloc(sizeof(int) * 3);
    p[0] = 1;
    p[1] = 2;
    p[2] = 3;
    s = 0;
    i = 0;
    while (i < 3) {
        s = s + *p;
        ++p;
        ++i;
    }
    return s * 10;
}
