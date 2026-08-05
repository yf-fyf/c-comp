int add(int a, int b) {
    return a + b;
}

int count_up(int n) {
    int i;
    int total;
    i = 0;
    total = 0;
    while (i < n) {
        ++i;
        total = add(total, i);
    }
    return total;
}

int main() {
    int k;
    k = 4;
    return count_up(++k) + add(--k, 1);
}
