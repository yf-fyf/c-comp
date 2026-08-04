// 再帰 — 隠しポインタが呼び出しごとに別の領域を指すことの確認
//
// 戻り値の受け取り領域を1個の共有バッファにしてしまう実装では、
// 再帰の内側の return が外側の領域を踏み潰してここで壊れる。
struct Acc { int n; int sum; };

struct Acc step(struct Acc a) {
    struct Acc r;

    if (a.n == 0) { return a; }

    r.n = a.n - 1;
    r.sum = a.sum + a.n;
    return step(r);        // 戻り値が戻り値になる入れ子
}

int main() {
    struct Acc a;
    struct Acc b;

    a.n = 5;
    a.sum = 0;

    b = step(a);

    if (b.n != 0) { return 1; }
    if (a.n != 5) { return 2; }        // 呼び出し元は無傷
    if (a.sum != 0) { return 3; }

    return b.sum;
}
