// void * — malloc の戻り値と任意の T * が、キャストなしで相互に変換されること
#include "lib.h"

struct Node {
    int val;
    struct Node *next;
};

int head_val(void *v) {
    struct Node *n;
    n = v;
    return n->val;
}

int main() {
    void *v;
    int *p;
    struct Node *n;

    v = malloc(sizeof(int) * 2);
    p = v;
    p[0] = 20;
    p[1] = 22;
    v = p;

    n = malloc(sizeof(struct Node));
    n->val = 5;
    n->next = NULL;

    return p[0] + p[1] + head_val(n);
}
