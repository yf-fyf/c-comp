#include "lib.h"

int call_count;
int total;

int add_and_count(int x) {
    total = total + x;
    call_count = call_count + 1;
    return total;
}

int main() {
    call_count = 0;
    total = 0;
    add_and_count(10);
    add_and_count(20);
    add_and_count(30);
    printf("%d\n", total);
    return call_count;
}
