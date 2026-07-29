// 短絡評価がないとゼロ除算になる
int main() {
    int x;
    int count;
    count = 0;

    x = 0;
    if (x != 0 && 100 / x > 2) { count = count + 1; }

    x = 10;
    if (x != 0 && 100 / x > 2) { count = count + 10; }

    x = 0;
    if (x == 0 || 100 / x > 2) { count = count + 100; }

    return count;
}
