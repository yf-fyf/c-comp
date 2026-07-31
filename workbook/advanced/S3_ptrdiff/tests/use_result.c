// 差の結果は int なので、そのまま計算に使える
#include "lib.h"

struct Pair { int x; int y; };

int main() {
    struct Pair *a;
    struct Pair *p;
    struct Pair *q;
    int n;

    a = malloc(sizeof(struct Pair) * 5);
    p = &a[1];
    q = &a[4];

    n = q - p;              // 3(Pair は 8 バイトだが、要素数は 3)
    if (n != 3) { return 1; }

    // 結果が int として扱われること(ポインタ演算にならないこと)
    if ((q - p) * 2 != 6) { return 2; }
    if ((q - p) + 1 != 4) { return 3; }

    return n * 10;
}
