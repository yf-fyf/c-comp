// 単純なループ: 命令数が反復回数に比例する
int main() {
    int i;
    int s;
    s = 0;
    for (i = 0; i < 200; i = i + 1) {
        s = s + i;
    }
    return s % 256;
}
