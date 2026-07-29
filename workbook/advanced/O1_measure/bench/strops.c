// 文字列の走査: char アクセスとポインタ演算
int my_strlen(char *s) {
    int n;
    n = 0;
    while (s[n] != 0) { n = n + 1; }
    return n;
}

int count_char(char *s, int c) {
    int n;
    int i;
    n = 0;
    i = 0;
    while (s[i] != 0) {
        if (s[i] == c) { n = n + 1; }
        i = i + 1;
    }
    return n;
}

int main() {
    char *s;
    int total;
    int r;
    s = "the quick brown fox jumps over the lazy dog";
    total = 0;
    for (r = 0; r < 20; r = r + 1) {
        total = total + my_strlen(s) + count_char(s, 111);
    }
    return total % 256;
}
