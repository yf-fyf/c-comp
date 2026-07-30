// f16: 三項演算子 — 値を持つ分岐（入れ子・関数引数でも使える）
int max(int a, int b) {
    return a > b ? a : b;
}

int main() {
    int x;
    x = max(3, 8) * 10;
    return x + (x == 80 ? 5 : 0);
}
