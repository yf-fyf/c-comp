// ポインタの差は「要素いくつ分か」になる
#include "lib.h"

int main() {
    int *a;
    int *p;
    int *q;

    a = malloc(sizeof(int) * 10);
    p = a;
    q = &a[7];

    // int は 4 バイトなので、アドレスの差は 28。要素数は 7
    return q - p;
}
