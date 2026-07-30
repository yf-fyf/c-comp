// f06: 制御(break) — i*i > 200 となる最初の i を返す
int main() {
    int i;
    int found;
    found = 0;
    for (i = 1; i <= 100; i = i + 1) {
        if (i * i > 200) {
            found = i;
            break;
        }
    }
    return found;
}
