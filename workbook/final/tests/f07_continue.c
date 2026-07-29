/* f07: 制御(continue) — 1..10 の和から 5 を除く */
int main() {
    int i;
    int s;
    s = 0;
    for (i = 1; i <= 10; i = i + 1) {
        if (i == 5) {
            continue;
        }
        s = s + i;
    }
    return s;
}
