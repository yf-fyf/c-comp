int my_abs(int x) {
    if (x < 0) return -x;
    return x;
}

int my_max(int a, int b) {
    if (a > b) return a;
    return b;
}

int my_pow(int base, int exp) {
    int result;
    int i;
    result = 1;
    for (i = 0; i < exp; i = i + 1) {
        result = result * base;
    }
    return result;
}
