// 左辺は1回だけ評価される — bump() が2回呼ばれたら calls が合わなくなる
#include "lib.h"

int calls;
int *slot;

int *bump() {
    calls = calls + 1;
    return slot;
}

int main() {
    slot = malloc(sizeof(int));
    *slot = 0;
    calls = 0;

    *bump() += 10;
    if (calls != 1) { return 1; }
    if (*slot != 10) { return 2; }

    *bump() *= 3;
    if (calls != 2) { return 3; }
    if (*slot != 30) { return 4; }

    return 42;
}
