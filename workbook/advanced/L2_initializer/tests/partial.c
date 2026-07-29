// 足りない要素は 0 で埋まる(C の規則)
int main() {
    int a[5] = {7, 8};
    if (a[0] != 7) { return 1; }
    if (a[1] != 8) { return 2; }
    if (a[2] != 0) { return 3; }
    if (a[4] != 0) { return 4; }
    return a[0] + a[1];
}
