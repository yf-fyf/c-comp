// main側のヘッダーと同じ構造体レイアウトを使う。
struct Box {
    int value;
};

struct Box *identity(struct Box *p) {
    return p;
}
