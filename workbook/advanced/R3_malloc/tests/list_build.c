// 自前 malloc で連結リストを作って走査する(コマ13 の再現)
#include "lib.h"

int heap_init(char *buf, int size);
char *my_malloc(int size);

struct Node {
    int val;
    struct Node *next;
};

int main() {
    char *pool;
    struct Node *head;
    struct Node *n;
    int sum;
    int i;

    pool = malloc(1024);
    heap_init(pool, 1024);
    head = 0;
    for (i = 1; i <= 3; i = i + 1) {
        n = my_malloc(sizeof(struct Node));
        n->val = i * 10;
        n->next = head;
        head = n;
    }
    sum = 0;
    while (head != 0) {
        sum = sum + head->val;
        head = head->next;
    }
    return sum;
}
