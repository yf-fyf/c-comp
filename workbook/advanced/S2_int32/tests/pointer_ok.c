// ポインタ演算は64bitのまま壊れていないこと(narrow しすぎの検出)
typedef struct Node { int val; struct Node *next; } Node;

int main() {
    int a[8];
    int *p;
    int i;
    Node n;
    Node *q;

    for (i = 0; i < 8; i = i + 1) { a[i] = i * 10; }

    p = a;
    p = p + 5;
    if (*p != 50) { return 1; }

    p = p - 2;
    if (*p != 30) { return 2; }

    if (a[7] != 70) { return 3; }

    n.val = 9;
    n.next = 0;
    q = &n;
    if (q->val != 9) { return 4; }

    return 55;
}
