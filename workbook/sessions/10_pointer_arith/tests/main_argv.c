// エントリポイントのもう一方の形 — int main(int argc, char **argv)
// テストランナーは引数を渡さないので argc は 1、argv[0] は実行ファイル名である。
int main(int argc, char **argv) {
    if (argc != 1) {
        return 1;
    }
    if (argv == 0) {
        return 2;
    }
    if (argv[0] == 0) {
        return 3;
    }
    if (*argv[0] == 0) {
        return 4;
    }
    return 40 + argc;
}
