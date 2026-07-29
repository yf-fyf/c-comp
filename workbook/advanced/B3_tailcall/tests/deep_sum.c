// 末尾再帰で 1..n の総和を求める。
// 末尾呼び出し最適化がないと、n が大きいときスタックがあふれて落ちる。
int sum_to(int n, int acc) {
    if (n == 0) {
        return acc;
    }
    return sum_to(n - 1, acc + n);
}

int main() {
    // 1..1000000 の総和は 500000500000。下位 8bit を返す
    return sum_to(1000000, 0) % 256;
}
