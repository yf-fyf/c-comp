// malloc 領域へのポインタアクセス: メモリアクセスと分岐が多い
#include "lib.h"

int main() {
    int *a;
    int i;
    int j;
    int t;
    int n;

    a = malloc(sizeof(int) * 20);
    n = 20;
    for (i = 0; i < n; i = i + 1) {
        a[i] = (n - i) * 7 % 31;
    }
    for (i = 0; i < n - 1; i = i + 1) {
        for (j = 0; j < n - 1 - i; j = j + 1) {
            if (a[j] > a[j + 1]) {
                t = a[j];
                a[j] = a[j + 1];
                a[j + 1] = t;
            }
        }
    }
    return a[0] * 10 + a[n - 1];
}
