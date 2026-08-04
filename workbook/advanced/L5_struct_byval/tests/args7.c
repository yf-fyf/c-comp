// 上限 — struct 値を返す関数は隠しポインタで1本使うので、ユーザ引数は7個まで
struct Pair { int total; int last; };

struct Pair pack(int a, int b, int c, int d, int e, int f, int g) {
    struct Pair p;
    p.total = a + b + c + d + e + f + g;
    p.last = g;
    return p;
}

int main() {
    struct Pair p;

    p = pack(1, 2, 3, 4, 5, 6, 7);
    if (p.last != 7) { return 1; }

    return p.total;
}
