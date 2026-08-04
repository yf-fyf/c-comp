// 値で受け取り、値で返す — 12 バイト(8+4)のコピーも確かめる
struct Box { int w; int h; int d; };

struct Box scale(struct Box b, int k) {
    b.w = b.w * k;         // 仮引数を書き換えても
    b.h = b.h * k;
    b.d = b.d * k;
    return b;              // 返るのはこの複製のほう
}

int main() {
    struct Box a;
    struct Box r;

    a.w = 1;
    a.h = 2;
    a.d = 3;

    r = scale(a, 2);

    if (a.w != 1) { return 1; }        // 呼び出し元は無傷
    if (a.h != 2) { return 2; }
    if (a.d != 3) { return 3; }

    if (r.w != 2) { return 4; }
    if (r.h != 4) { return 5; }
    if (r.d != 6) { return 6; }

    return r.w + r.h + r.d;
}
