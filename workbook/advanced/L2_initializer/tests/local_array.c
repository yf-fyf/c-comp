// ローカル配列の初期化子リスト
int main() {
    int a[3] = {1, 2, 3};
    int sum;
    int i;
    sum = 0;
    for (i = 0; i < 3; i = i + 1) { sum = sum + a[i]; }
    if (sum != 6) { return 1; }
    if (a[0] != 1) { return 2; }
    if (a[2] != 3) { return 3; }
    return 42;
}
