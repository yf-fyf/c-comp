/* f05: 制御(for) — for ループで階乗 5! = 120 */
int main() {
    int i;
    int r;
    r = 1;
    for (i = 1; i <= 5; i = i + 1) {
        r = r * i;
    }
    return r;
}
