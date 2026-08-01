// exit — 終了コードを指定してその場でプログラムを終わらせる（戻ってこない）
#include "lib.h"

int main() {
    printf("before exit\n");
    exit(7);
    printf("not reached\n");
    return 1;
}
