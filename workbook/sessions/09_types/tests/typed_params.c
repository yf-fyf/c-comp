// 型付きパラメータ単体 — char / int / ポインタの引数が、それぞれの幅で
// スタックに退避され読み戻せるか（_alloc_params と関数プロローグの退避）。
int add_to(char c, int n, int *p) {
    if (c != 65) {
        return 1;
    }
    if (n != 7) {
        return 2;
    }
    *p = *p + c;
    return 0;
}

int main() {
    int x;
    char c;
    int r;
    x = 10;
    c = 'A';
    r = add_to(c, 7, &x);
    if (r != 0) {
        return r;
    }
    return x;
}
