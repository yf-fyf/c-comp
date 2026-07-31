// 短絡評価がないと NULL 参照でクラッシュする
struct Node { int val; struct Node *next; };

int main() {
    struct Node n;
    struct Node *p;
    n.val = 7;

    p = 0;
    // 短絡すれば p->val は評価されない
    if (p != 0 && p->val > 0) {
        return 1;
    }

    p = &n;
    if (p != 0 && p->val > 0) {
        return p->val;
    }
    return 2;
}
