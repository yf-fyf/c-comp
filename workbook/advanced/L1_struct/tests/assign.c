// 構造体の代入(まるごとコピー)
struct Point { int x; int y; };

int main() {
    struct Point p;
    struct Point q;
    p.x = 3;
    p.y = 4;

    q = p;                 // まるごとコピー
    if (q.x != 3) { return 1; }
    if (q.y != 4) { return 2; }

    p.x = 99;              // コピーなので q は影響を受けない
    if (q.x != 3) { return 3; }

    return q.x + q.y;
}
