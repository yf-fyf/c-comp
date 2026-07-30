// f12: 構造体 — ドットとアロー両方を使用
struct Entry {
    int val;
    int mul;
};

int compute(struct Entry *e) {
    return e->val * e->mul;
}

int main() {
    struct Entry e;
    e.val = 5;
    e.mul = 7;
    return compute(&e);
}
