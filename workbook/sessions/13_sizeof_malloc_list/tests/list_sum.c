#include "lib.h"

typedef struct Node {
    int val;
    struct Node *next;
} Node;

int list_sum(Node *head) {
    int sum;
    sum = 0;
    while (head != 0) {
        sum = sum + head->val;
        head = head->next;
    }
    return sum;
}

Node *new_node(int v) {
    Node *n;
    n = malloc(sizeof(Node));
    n->val = v;
    n->next = 0;
    return n;
}

int main() {
    Node *a;
    Node *b;
    Node *c;
    a = new_node(10);
    b = new_node(20);
    c = new_node(30);
    a->next = b;
    b->next = c;
    return list_sum(a);
}
