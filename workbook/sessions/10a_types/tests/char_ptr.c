// char へのポインタ — *p の読み書きが 1 バイト幅（lb/sb）になり、int * の 4 バイト幅と
// 取り違えられていないことを確かめる。ポインタ演算も添字も使わない。
int main() {
    char c;
    char d;
    char *p;
    int n;
    int *q;
    c = 65;
    d = 0;
    p = &c;
    if (*p != 65) {
        return 1;
    }
    *p = 200;
    if (c != -56) {
        return 2;
    }
    p = &d;
    *p = c + 100;
    if (d != 44) {
        return 3;
    }
    n = 1000;
    q = &n;
    *q = *q + 1;
    if (n != 1001) {
        return 4;
    }
    if (*q != 1001) {
        return 5;
    }
    return d + 6;
}
