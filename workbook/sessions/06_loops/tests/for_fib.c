int main() {
    int i;
    int fib_a;
    int fib_b;
    int tmp;
    fib_a = 0;
    fib_b = 1;
    for (i = 0; i < 10; i = i + 1) {
        tmp   = fib_b;
        fib_b = fib_a + fib_b;
        fib_a = tmp;
    }
    return fib_a;
}
