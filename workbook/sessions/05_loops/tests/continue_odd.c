int main() {
    int i;
    int sum;
    i = 1;
    sum = 0;
    for (i = 1; i <= 10; i = i + 1) {
        if (i % 2 == 0) {
            continue;
        }
        sum = sum + i;
    }
    return sum;
}
