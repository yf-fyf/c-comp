int add(int a, int b) {
    return a + b;
}

int twice(int n) {
    return n * 2;
}

int main() {
    int a;
    a = 3;
    return a * (twice(4) + add(1, 2) * 2) + twice(add(2, 3));
}
