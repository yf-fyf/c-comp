// 構造体の値返し — 戻り値を受け取り、メンバを直接読む
struct Point { int x; int y; };

struct Point make(int x, int y) {
    struct Point p;
    p.x = x;
    p.y = y;
    return p;
}

int main() {
    struct Point q;

    q = make(5, 6);
    if (q.x != 5) { return 1; }
    if (q.y != 6) { return 2; }

    if (make(1, 2).x != 1) { return 3; }   // 戻り値のメンバを直接読む
    if (make(1, 2).y != 2) { return 4; }

    q = make(7, 8);                        // 同じ変数へ2回目
    if (q.x != 7) { return 5; }
    if (q.y != 8) { return 6; }

    return make(2, 3).x * make(2, 3).y;
}
