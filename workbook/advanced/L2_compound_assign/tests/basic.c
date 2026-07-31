// 複合代入の基本 — += -= *= /= %= を順に確かめる
int main() {
    int x;
    int y;
    x = 10;
    x += 3;
    if (x != 13) { return 1; }
    x -= 5;
    if (x != 8) { return 2; }
    x *= 4;
    if (x != 32) { return 3; }
    x /= 3;
    if (x != 10) { return 4; }
    x %= 4;
    if (x != 2) { return 5; }

    // 右結合 + 式としての値(x に 3 を足した結果が y にも足される)
    y = 0;
    y += x += 3;
    if (x != 5) { return 6; }
    if (y != 5) { return 7; }

    return 42;
}
