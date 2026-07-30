#include "lib.h"

int main() {
    int *a;
    int *p;
    a = malloc(sizeof(int) * 4);
    a[0] = 10;
    a[1] = 20;
    a[2] = 30;
    a[3] = 40;
    p = a;
    return *(p + 2) + *(p + 3);
}
