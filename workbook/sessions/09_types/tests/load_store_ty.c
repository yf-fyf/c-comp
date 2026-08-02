// 型付きロード・ストア単体 — char は lb/sb、int は lw/sw、ポインタは ld/sd を選べているか。
// ポインタ演算も添字も使わないので、_load_ty / _store_ty と type_of_* の切り分けだけを見る
// （実装手順 2〜3 の直後に通る）。
int main() {
    char c;
    int n;
    int *p;
    c = 9;
    n = 4;
    p = &n;
    if (c != 9) {
        return 1;
    }
    if (n != 4) {
        return 2;
    }
    if (*p != 4) {
        return 3;
    }
    *p = 30;
    if (n != 30) {
        return 4;
    }
    return n;
}
