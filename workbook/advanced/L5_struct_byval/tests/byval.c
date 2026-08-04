// 構造体の値渡し — 呼ばれ側の変更が呼び出し元に伝わらないこと
struct Point { int x; int y; };

int sum(struct Point p) {
    p.x = 100;             // 仮引数は自分専用の複製。呼び出し元には影響しない
    return p.x + p.y;
}

int main() {
    struct Point a;
    struct Point *q;

    a.x = 3;
    a.y = 4;

    if (sum(a) != 104) { return 1; }
    if (a.x != 3) { return 2; }        // 元の構造体は変わっていない
    if (a.y != 4) { return 3; }

    q = &a;
    if (sum(*q) != 104) { return 4; }  // *p も値渡しできる
    if (a.x != 3) { return 5; }

    return a.x + a.y;
}
