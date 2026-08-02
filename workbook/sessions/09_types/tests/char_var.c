// char 変数 — 1 バイトの読み書き（lb / sb）、int への昇格、代入時の下位 8 ビットへの縮小
int main() {
    char c;
    char d;
    int n;
    c = 'A';
    d = c + 2;
    n = d;
    if (n != 67) {
        return 1;
    }
    c = 321;
    if (c != 65) {
        return 2;
    }
    return n;
}
