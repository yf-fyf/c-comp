// コマ4〜6の機能（三項演算・前置増減・一時値を積んだ状態での関数呼び出し）が、
// 型を導入したコマ8のコンパイラでもそのまま動くことを確かめる。
// codegen() を全 case 再列挙にすると Cond や PreInc/PreDec が落ち、
// _push_a0 / _pop_into を定義し直すと call 直前の 16 バイト整列が崩れる。
int add(int a, int b) {
    return a + b;
}

int pick(char c, int *p) {
    return c > 60 ? *p + c : *p - c;
}

int main() {
    char c;
    char d;
    int n;
    int *p;
    int r;
    c = 'A';
    d = 5;
    n = 10;
    p = &n;
    ++n;
    r = pick(c, p);
    --r;
    // 三項演算の型は _type_of_expr の Cond が決める。ここが char * にならないと
    // 1 バイトのロード（lb）が選ばれず、読み出した値が壊れる。
    if (*(n > 0 ? &d : &c) != 5) {
        return 1;
    }
    // 左辺 r * 2 を一時値として積んだまま右辺で call するので、
    // call 直前のスタックは 16 バイト境界からずれている。
    return r * 2 + add(pick(c, p), n);
}
