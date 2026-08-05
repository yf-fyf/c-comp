// コマ4〜6の機能（三項演算・前置増減・一時値を積んだ状態での関数呼び出し）が、
// & と * を足したコマ7のコンパイラでもそのまま動くことを確かめる。
// codegen() のディスパッチを Addr / Deref だけ足して委譲する形にしていないと、
// Cond や PreInc/PreDec が「未対応の式」で落ちる。
int add(int a, int b) {
    return a + b;
}

int deref_add(int *p, int n) {
    return *p + n;
}

int main() {
    int x;
    int y;
    int *p;
    x = 3;
    p = &x;
    ++x;
    y = *p > 3 ? add(*p, 6) : 0;
    --y;
    // 左辺 y * 2 を一時値として積んだまま右辺で call するので、
    // call 直前のスタックは 16 バイト境界からずれている。
    return y * 2 + add(deref_add(p, 1), *p);
}
