// 退行確認 — sizeof(型名) 形式はこれまでどおり動く
struct Point {
    int x;
    int y;
};

int main() {
    if (sizeof(int) != 4) { return 1; }
    if (sizeof(char) != 1) { return 2; }
    if (sizeof(int*) != 8) { return 3; }
    if (sizeof(char*) != 8) { return 4; }
    if (sizeof(void*) != 8) { return 5; }
    if (sizeof(struct Point) != 8) { return 6; }
    if (sizeof(struct Point*) != 8) { return 7; }

    // 式の中に置いても優先順位は変わらない
    if (sizeof(int) * 2 != 8) { return 8; }

    return 42;
}
