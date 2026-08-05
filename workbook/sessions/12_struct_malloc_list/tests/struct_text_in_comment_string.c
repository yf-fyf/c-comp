// コメントや文字列リテラルの中の struct 風テキストを定義と誤認しないこと。
struct T {
    int a;
    int b;
};

// 下の 2 つは「定義」ではない。誤認すると struct T のレイアウトが壊れる。
// struct T { char c; };

int main() {
    char *msg;
    struct T t;
    msg = "struct T { char c; };";
    t.a = 1;
    t.b = 2;
    // sizeof(struct T) は 8。msg[0] は 's'（115）。
    return sizeof(struct T) + t.a + t.b + msg[0];
}
