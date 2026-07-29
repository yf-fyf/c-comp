/* f11: 配列 — ポインタ渡しで配列の総和 */
int sum(int *a, int n) {
    int i;
    int s;
    s = 0;
    for (i = 0; i < n; i = i + 1) {
        s = s + a[i];
    }
    return s;
}

int main() {
    int a[5];
    a[0] = 10;
    a[1] = 20;
    a[2] = 30;
    a[3] = 5;
    a[4] = 7;
    return sum(a, 5);
}
