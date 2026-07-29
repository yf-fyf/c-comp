// 再帰: 関数呼び出しが多い
int fib(int n) {
    if (n <= 1) { return n; }
    return fib(n - 1) + fib(n - 2);
}

int main() {
    return fib(15) % 256;
}
