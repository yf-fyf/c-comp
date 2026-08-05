// sizeof(型名) 単体 — 翻訳時定数として正しいサイズが出るか。
// ポインタ演算・添字・型付きロードには依存しない（実装手順 6 の直後に通る）。
int main() {
    if (sizeof(char) != 1) {
        return 1;
    }
    if (sizeof(int) != 4) {
        return 2;
    }
    if (sizeof(char *) != 8) {
        return 3;
    }
    if (sizeof(int *) != 8) {
        return 4;
    }
    if (sizeof(int **) != 8) {
        return 5;
    }
    return sizeof(int) * 10;
}
