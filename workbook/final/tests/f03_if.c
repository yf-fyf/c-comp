/* f03: 制御(if) — if/else if/else チェーン */
int grade(int s) {
    if (s >= 90) {
        return 1;
    } else if (s >= 70) {
        return 2;
    } else {
        return 3;
    }
}

int main() {
    return grade(75);
}
