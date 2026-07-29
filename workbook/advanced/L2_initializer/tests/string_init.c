// char 配列を文字列で初期化する(NUL 終端つき)
int my_strlen(char *s) {
    int n;
    n = 0;
    while (s[n] != 0) { n = n + 1; }
    return n;
}

int main() {
    char s[6] = "hello";
    char c[4] = {97, 98, 99, 0};

    if (s[0] != 104) { return 1; }       // 'h'
    if (s[4] != 111) { return 2; }       // 'o'
    if (s[5] != 0) { return 3; }         // NUL 終端
    if (my_strlen(s) != 5) { return 4; }
    if (my_strlen(c) != 3) { return 5; }

    return my_strlen(s) + my_strlen(c);
}
