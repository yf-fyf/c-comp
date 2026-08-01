// 戻り値のない関数 — void の戻り値型、明示的な return;、本体末尾での終了
void add_to(int *dst, int v) {
    *dst = *dst + v;
    return;
}

void clear(int *dst) {
    *dst = 0;
}

int main() {
    int acc;
    clear(&acc);
    add_to(&acc, 10);
    add_to(&acc, 5);
    return acc;
}
