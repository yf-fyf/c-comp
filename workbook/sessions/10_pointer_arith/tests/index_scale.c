// 添字のスケール単体 — a[i] のアドレス計算が要素サイズ 1 / 4 / 8 で切り替わるか。
// _scale_index と codegen_lval_Index を、要素型の違いだけで揺さぶる
// （実装手順 4〜5 の直後に通る）。
#include "lib.h"

int main() {
    char *cs;
    int *is;
    int **ps;
    int x;
    int y;
    cs = malloc(3);
    cs[0] = 1;
    cs[1] = 2;
    cs[2] = 3;
    is = malloc(sizeof(int) * 3);
    is[0] = 10;
    is[1] = 20;
    is[2] = 42;
    x = 100;
    y = 200;
    ps = malloc(sizeof(int *) * 2);
    ps[0] = &x;
    ps[1] = &y;
    if (cs[0] != 1) {
        return 1;
    }
    if (cs[2] != 3) {
        return 2;
    }
    if (is[0] != 10) {
        return 3;
    }
    if (is[2] != 42) {
        return 4;
    }
    if (*ps[0] != 100) {
        return 5;
    }
    if (*ps[1] != 200) {
        return 6;
    }
    return is[2];
}
