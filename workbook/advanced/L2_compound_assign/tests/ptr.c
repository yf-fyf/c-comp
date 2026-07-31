// ポインタへの += -= は要素サイズぶん進む(バイト数ではない)
#include "lib.h"

int main() {
    int *a;
    int *p;
    char *s;

    a = malloc(sizeof(int) * 5);
    a[0] = 10;
    a[1] = 20;
    a[2] = 30;
    a[3] = 40;
    a[4] = 50;

    p = a;
    p += 2;
    if (*p != 30) { return 1; }
    p -= 1;
    if (*p != 20) { return 2; }
    p += 3;
    if (*p != 50) { return 3; }

    // char は要素サイズ 1
    s = malloc(4);
    s[0] = 65;
    s[1] = 66;
    s[2] = 67;
    s[3] = 0;
    s += 2;
    if (*s != 67) { return 4; }

    return 42;
}
