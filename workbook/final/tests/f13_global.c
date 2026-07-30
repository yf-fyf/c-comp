// f13: グローバル変数 — 複数関数から共有するアキュムレータ
int total;

void add_to_total(int n) {
    total = total + n;
}

int main() {
    total = 0;
    add_to_total(15);
    add_to_total(20);
    add_to_total(7);
    return total;
}
