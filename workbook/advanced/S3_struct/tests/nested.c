// ポインタ・フィールドを持つ構造体の代入
struct Point { int x; int y; };
struct Line { struct Point *a; struct Point *b; };

int main() {
    struct Point p;
    struct Point q;
    struct Line l;
    struct Line m;

    p.x = 1; p.y = 2;
    q.x = 10; q.y = 20;

    l.a = &p;
    l.b = &q;

    if (l.a->x != 1) { return 1; }
    if (l.b->y != 20) { return 2; }

    m = l;                 // ポインタ2本(16バイト)をまるごとコピー
    if (m.a->x != 1) { return 3; }
    if (m.b->y != 20) { return 4; }

    // ポインタのコピーなので m.a と l.a は同じ Point を指す
    p.x = 99;
    if (m.a->x != 99) { return 5; }

    return m.a->x + m.a->y + m.b->x + m.b->y;
}
