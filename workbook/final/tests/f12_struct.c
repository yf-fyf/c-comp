/* f12: 構造体 — ドットとアロー両方を使用 */
typedef struct {
    int val;
    int mul;
} Entry;

int compute(Entry *e) {
    return e->val * e->mul;
}

int main() {
    Entry e;
    e.val = 5;
    e.mul = 7;
    return compute(&e);
}
