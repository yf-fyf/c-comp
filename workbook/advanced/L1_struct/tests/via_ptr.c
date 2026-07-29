// ポインタ経由の構造体代入
typedef struct Box { int w; int h; int d; } Box;

int fill(Box *dst, Box *src) {
    *dst = *src;           // ポインタの先どうしをコピー
    return 0;
}

int main() {
    Box a;
    Box b;
    a.w = 2; a.h = 3; a.d = 5;

    fill(&b, &a);
    if (b.w != 2) { return 1; }
    if (b.h != 3) { return 2; }
    if (b.d != 5) { return 3; }

    return b.w * b.h * b.d;
}
