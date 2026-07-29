// ポインタの差は「要素いくつ分か」になる
int main() {
    int a[10];
    int *p;
    int *q;

    p = a;
    q = &a[7];

    // int は 4 バイトなので、アドレスの差は 28。要素数は 7
    return q - p;
}
