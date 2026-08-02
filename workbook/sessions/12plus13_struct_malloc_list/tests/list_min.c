#include "lib.h"

struct Node {
    int val;
    struct Node *next;
};

int main() {
    struct Node *n;
    n = malloc(sizeof(struct Node));
    n->val = 10;
    n->next = NULL;
    return n->val;
}
