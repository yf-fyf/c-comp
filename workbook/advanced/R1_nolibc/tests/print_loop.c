// syscall.s とリンクして libc なしで動かす C プログラム。
// 1文字ずつ書き出して "abc\n" を表示し、終了コード 3 を返す。
int sys_write(int fd, char *buf, int len);

int main() {
    char buf[4];
    int i;
    i = 0;
    while (i < 3) {
        buf[i] = 97 + i;      // 'a' + i
        i = i + 1;
    }
    buf[3] = 10;              // '\n'
    sys_write(1, buf, 4);
    return 3;
}
