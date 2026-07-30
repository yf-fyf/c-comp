// 文字列走査は自作する（strlen 相当は lib.h にない）
int my_strlen(char *s) {
    int n;
    n = 0;
    while (s[n] != '\0') {
        n = n + 1;
    }
    return n;
}

int main() {
    return my_strlen("abc");
}
