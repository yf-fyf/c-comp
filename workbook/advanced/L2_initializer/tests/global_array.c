// グローバル配列の初期化(.data に置かれる)
int g[4] = {10, 20, 30, 40};
int zeros[3];

int main() {
    int sum;
    int i;
    sum = 0;
    for (i = 0; i < 4; i = i + 1) { sum = sum + g[i]; }
    if (sum != 100) { return 1; }
    if (zeros[1] != 0) { return 2; }     // 初期化なしは 0
    return sum / 2;
}
