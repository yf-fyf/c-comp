// 呼び出しの入れ子 — 戻り値をそのまま実引数に渡す
struct Point { int x; int y; };

struct Point make(int x, int y) {
    struct Point p;
    p.x = x;
    p.y = y;
    return p;
}

int sum(struct Point p) {
    return p.x + p.y;
}

struct Point add(struct Point a, struct Point b) {
    return make(a.x + b.x, a.y + b.y);
}

int main() {
    if (sum(make(3, 4)) != 7) { return 1; }
    if (sum(add(make(1, 2), make(10, 20))) != 33) { return 2; }
    if (add(make(1, 2), make(10, 20)).x != 11) { return 3; }
    return sum(add(make(1, 1), make(2, 3)));
}
