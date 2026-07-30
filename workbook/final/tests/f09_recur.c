// f09: 関数(再帰) — フィボナッチ数列 fib(10) = 55
int fib(int n) {
    if (n <= 1) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

int main() {
    return fib(10);
}
