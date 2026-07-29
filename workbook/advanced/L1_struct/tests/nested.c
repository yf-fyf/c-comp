// ネストした構造体と、そのメンバへの代入
typedef struct Point { int x; int y; } Point;
typedef struct Line { Point a; Point b; } Line;

int main() {
    Point p;
    Line l;
    Line m;

    p.x = 1; p.y = 2;
    l.a = p;               // ネストしたメンバへの構造体代入
    l.b.x = 10;
    l.b.y = 20;

    if (l.a.x != 1) { return 1; }
    if (l.a.y != 2) { return 2; }

    m = l;                 // 16 バイトまるごとコピー
    if (m.a.x != 1) { return 3; }
    if (m.b.y != 20) { return 4; }

    return m.a.x + m.a.y + m.b.x + m.b.y;
}
