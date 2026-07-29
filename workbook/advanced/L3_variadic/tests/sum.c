// 可変長引数の関数を「定義」する
// __arg(i) は i 番目の引数を返す組み込み関数(0 番目は最初の名前つき引数)
int __arg(int i);

int sum(int n, ...) {
    int total;
    int i;
    total = 0;
    for (i = 1; i <= n; i = i + 1) {
        total = total + __arg(i);
    }
    return total;
}

int main() {
    if (sum(3, 10, 20, 30) != 60) { return 1; }
    if (sum(1, 7) != 7) { return 2; }
    if (sum(0) != 0) { return 3; }
    return sum(4, 1, 2, 3, 4);
}
