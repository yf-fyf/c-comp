// 可変長引数で最大値を求める
int __arg(int i);

int max_of(int n, ...) {
    int best;
    int i;
    int v;
    best = __arg(1);
    for (i = 2; i <= n; i = i + 1) {
        v = __arg(i);
        if (v > best) { best = v; }
    }
    return best;
}

int main() {
    if (max_of(3, 5, 9, 2) != 9) { return 1; }
    if (max_of(2, 40, 8) != 40) { return 2; }
    if (max_of(1, 7) != 7) { return 3; }
    return max_of(5, 1, 6, 3, 6, 2);
}
