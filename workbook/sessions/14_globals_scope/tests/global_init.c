// グローバル変数は 0 に初期化される（明示的な代入なしで使い始められる）
int base;

int add_base(int x) {
    base = base + x;
    return base;
}

int main() {
    int r;
    r = add_base(7);
    return r + 5;
}
