int swap(int *a, int *b) {
    int tmp;
    tmp = *a;
    *a = *b;
    *b = tmp;
    return 0;
}

int main() {
    int x;
    int y;
    x = 3;
    y = 7;
    swap(&x, &y);
    return x + y * 10;
}
