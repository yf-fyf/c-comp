int main() {
    int a[5];
    int i;
    int sum;
    a[0] = 1;
    a[1] = 2;
    a[2] = 3;
    a[3] = 4;
    a[4] = 5;
    sum = 0;
    for (i = 0; i < 5; i = i + 1) {
        sum = sum + a[i];
    }
    return sum;
}
