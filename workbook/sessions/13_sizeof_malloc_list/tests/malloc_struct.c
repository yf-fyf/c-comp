#include "lib.h"

struct Box {
    int val;
    int doubled;
};

struct Box *make_box(int v) {
    struct Box *b;
    b = malloc(sizeof(struct Box));
    b->val = v;
    b->doubled = v * 2;
    return b;
}

int main() {
    struct Box *b1;
    struct Box *b2;
    b1 = make_box(7);
    b2 = make_box(3);
    return b1->doubled + b2->val;
}
