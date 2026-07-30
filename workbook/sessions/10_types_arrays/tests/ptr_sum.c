#include "lib.h"

int main() {
    int *a;
    int i;
    int sum;
    a = malloc(sizeof(int) * 5);
    a[0] = 1;
    a[1] = 2;
    a[2] = 3;
    a[3] = 4;
    a[4] = 5;
    sum = 0;
    for (i = 0; i < 5; ++i) {
        sum = sum + a[i];
    }
    return sum;
}
