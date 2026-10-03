struct Box {
    int value;
};

struct Box *identity(struct Box *p) {
    return p;
}

int main() {
    struct Box a;
    struct Box b;
    a.value = 7;
    b.value = 9;
    identity(&a)->value = 42;
    // 入れ子の呼出しと三項演算子を経由しても struct Box * が伝わる。
    return identity(identity(&a))->value + (1 ? identity(&a) : &b)->value;
}
