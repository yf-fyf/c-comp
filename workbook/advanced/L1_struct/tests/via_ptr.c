// ポインタ経由の構造体代入
struct Box { int w; int h; int d; };

int fill(struct Box *dst, struct Box *src) {
    *dst = *src;           // ポインタの先どうしをコピー
    return 0;
}

int main() {
    struct Box a;
    struct Box b;
    a.w = 2; a.h = 3; a.d = 5;

    fill(&b, &a);
    if (b.w != 2) { return 1; }
    if (b.h != 3) { return 2; }
    if (b.d != 5) { return 3; }

    return b.w * b.h * b.d;
}
