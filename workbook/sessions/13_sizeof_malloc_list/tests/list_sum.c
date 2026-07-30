#include "lib.h"

struct Node {
    int val;
    struct Node *next;
};

int list_sum(struct Node *head) {
    int sum;
    sum = 0;
    while (head != NULL) {
        sum = sum + head->val;
        head = head->next;
    }
    return sum;
}

struct Node *new_node(int v) {
    struct Node *n;
    n = malloc(sizeof(struct Node));
    n->val = v;
    n->next = NULL;
    return n;
}

int main() {
    struct Node *a;
    struct Node *b;
    struct Node *c;
    a = new_node(10);
    b = new_node(20);
    c = new_node(30);
    a->next = b;
    b->next = c;
    return list_sum(a);
}
