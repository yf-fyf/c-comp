// 3重ループ: malloc 領域へのポインタアクセスが多い
#include "lib.h"

int main() {
    int *a;
    int *b;
    int *c;
    int i;
    int j;
    int k;
    int t;

    a = malloc(sizeof(int) * 36);
    b = malloc(sizeof(int) * 36);
    c = malloc(sizeof(int) * 36);
    for (i = 0; i < 6; i = i + 1) {
        for (j = 0; j < 6; j = j + 1) {
            a[i * 6 + j] = i + j;
            b[i * 6 + j] = i - j;
            c[i * 6 + j] = 0;
        }
    }
    for (i = 0; i < 6; i = i + 1) {
        for (j = 0; j < 6; j = j + 1) {
            t = 0;
            for (k = 0; k < 6; k = k + 1) {
                t = t + a[i * 6 + k] * b[k * 6 + j];
            }
            c[i * 6 + j] = t;
        }
    }
    return c[0] % 256;
}
