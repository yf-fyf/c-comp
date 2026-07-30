// f08: 関数 — 多引数関数の合成呼び出し
int max(int a, int b) {
    if (a > b) {
        return a;
    }
    return b;
}

int max3(int a, int b, int c) {
    return max(max(a, b), c);
}

int main() {
    return max3(10, 42, 7);
}
