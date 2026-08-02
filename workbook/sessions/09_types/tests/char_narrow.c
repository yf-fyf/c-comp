// char の境界 — 代入で下位 8 ビットへ縮小され（sb）、読み出しで符号拡張される（lb）ことを
// 127 / 128 / 255 / -1 / 256 の境界で確かめる。ポインタも添字も使わない。
int main() {
    char c;
    int n;
    c = 127;
    if (c != 127) {
        return 1;
    }
    c = 128;
    if (c != -128) {
        return 2;
    }
    c = 255;
    if (c != -1) {
        return 3;
    }
    c = -1;
    if (c != -1) {
        return 4;
    }
    c = 256;
    if (c != 0) {
        return 5;
    }
    c = 300;
    if (c != 44) {
        return 6;
    }
    n = c + 1;
    if (n != 45) {
        return 7;
    }
    c = n;
    return c;
}
