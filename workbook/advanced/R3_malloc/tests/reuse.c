// 解放したブロックが再利用されることを確かめる
#include "lib.h"

int heap_init(char *buf, int size);
char *my_malloc(int size);
int my_free(char *p);
int heap_used();

int main() {
    char *pool;
    char *a;
    char *b;
    char *c;

    pool = malloc(1024);
    heap_init(pool, 1024);
    a = my_malloc(16);
    b = my_malloc(16);
    my_free(b);
    c = my_malloc(16);      // b の跡地が再利用されるはず

    if (b != c) {
        return 1;           // 再利用されなかった
    }
    if (heap_used() != 32) {
        return 2;           // 使用量が合わない(16 x 2)
    }
    return 0;
}
