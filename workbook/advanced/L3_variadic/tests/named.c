// 名前つき引数も __arg で読めること、通常の関数が壊れていないこと
int __arg(int i);

int tagged(int tag, int n, ...) {
    int total;
    int i;
    if (__arg(0) != tag) { return 100; }     // 0 番目は第1引数
    if (__arg(1) != n) { return 101; }       // 1 番目は第2引数
    total = 0;
    for (i = 2; i < 2 + n; i = i + 1) {
        total = total + __arg(i);
    }
    return tag * 1000 + total;
}

int plain(int a, int b) { return a - b; }    // 可変長でない関数

int main() {
    if (plain(9, 4) != 5) { return 1; }
    // 終了コードは 0〜255 なので小さくして返す
    return (tagged(2, 3, 100, 200, 300) - 2000) / 10;
}
