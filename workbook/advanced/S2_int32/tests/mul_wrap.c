// 掛け算も32bitで折り返す
int main() {
    int x;
    int y;

    x = 100000;
    y = x * x;           // 10^10 は int に収まらない → 折り返す
    if (y == 10000000000) { return 1; }   // 64bit のままならこうなる
    if (y != 1410065408) { return 2; }    // 32bit で折り返した値

    x = 65536;
    if (x * x != 0) { return 3; }         // 2^32 は 32bit では 0

    return 7;
}
