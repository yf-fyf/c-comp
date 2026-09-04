int main() {
    int a;
    int b;
    int t;
    int f;
    int r;
    a = 3;
    b = 8;
    t = 0;
    f = 0;
    // 選ばれなかった枝(ここでは真の枝)も評価してしまう実装だと、
    // t が 0 のままにならず 3 になる。r + t * 100 + f で見分ける。
    r = a > b ? (t = a) : (f = b);
    return r + t * 100 + f;
}
