// f10: ポインタ — swap 関数でポインタ渡し
void swap(int *a, int *b) {
    int t;
    t = *a;
    *a = *b;
    *b = t;
}

int main() {
    int x;
    int y;
    x = 3;
    y = 42;
    swap(&x, &y);
    return x;
}
