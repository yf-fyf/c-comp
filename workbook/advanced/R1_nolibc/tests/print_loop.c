// syscall.s とリンクして libc なしで動かす C プログラム。
// 1文字ずつ書き出して "abc\n" を表示し、終了コード 3 を返す。
int sys_write(int fd, char *buf, int len);

int main() {
    char c;
    int i;
    i = 0;
    while (i < 3) {
        c = 97 + i;           // 'a' + i
        sys_write(1, &c, 1);
        i = i + 1;
    }
    c = 10;                   // '\n'
    sys_write(1, &c, 1);
    return 3;
}
