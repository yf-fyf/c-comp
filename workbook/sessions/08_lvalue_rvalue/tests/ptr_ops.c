int main() {
    int a;
    int b;
    int *p;
    a = 10;
    b = 20;
    p = &a;
    *p = *p + 5;
    p = &b;
    *p = *p * 2;
    return a + b;
}
