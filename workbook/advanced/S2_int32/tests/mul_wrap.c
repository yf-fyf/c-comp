// 掛け算も32bitで折り返す
int main() {
    int x;
    int y;

    x = 100000;
    y = x * x;           // 10^10 は int に収まらない → 折り返す
    if (y != 1410065408) { return 1; }    // 32bit で折り返した値と一致するはず

    x = 65536;
    if (x * x != 0) { return 2; }         // 2^32 は 32bit では 0

    return 7;
}
