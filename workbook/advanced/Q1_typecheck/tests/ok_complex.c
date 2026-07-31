#include "lib.h"

int fib(int n) {
    if (n <= 1) { return n; }
    return fib(n - 1) + fib(n - 2);
}
int g;
int main() {
    int *a;
    int i;
    int *p;
    g = 0;
    a = malloc(sizeof(int) * 5);
    for (i = 0; i < 5; i = i + 1) { a[i] = i; }
    p = a;
    *p = 10;
    ++i;
    g = (g < 10) ? g + 1 : g;
    printf("%d\n", fib(10));
    return a[0] + g;
}
