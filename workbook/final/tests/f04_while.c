/* f04: 制御(while) — while ループで累積和 */
int main() {
    int i;
    int s;
    i = 1;
    s = 0;
    while (i <= 10) {
        s = s + i;
        i = i + 1;
    }
    return s;
}
