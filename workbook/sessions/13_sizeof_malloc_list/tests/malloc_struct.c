#include "lib.h"

typedef struct {
    int val;
    int doubled;
} Box;

Box *make_box(int v) {
    Box *b;
    b = malloc(sizeof(Box));
    b->val = v;
    b->doubled = v * 2;
    return b;
}

int main() {
    Box *b1;
    Box *b2;
    b1 = make_box(7);
    b2 = make_box(3);
    return b1->doubled + b2->val;
}
