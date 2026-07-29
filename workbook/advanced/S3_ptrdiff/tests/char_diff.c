// char* の差は 1 バイト単位(要素サイズが 1)
int my_strlen(char *s) {
    char *p;
    p = s;
    while (*p != 0) {
        p = p + 1;
    }
    return p - s;      // 進んだ要素数 = 文字数
}

int main() {
    return my_strlen("hello!");
}
