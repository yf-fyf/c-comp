// 式の走査 — 添字・ポインタ加算・間接参照・比較の奥にある文字列リテラル。
// printf を使わないので、文字列リテラルを式として評価する部分だけを確かめられる。
int main() {
    if ("abc"[1] != 'b') {
        return 1;
    }
    if (*("abc" + 2) != 'c') {
        return 2;
    }
    if ("abcde"[0] < "abcde"[4]) {
        return 42;
    }
    return 3;
}
