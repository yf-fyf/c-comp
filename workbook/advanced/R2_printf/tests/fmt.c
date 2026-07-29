// printf1 の書式指定を確認する
int print_str(char *s);
int print_int(int n);
int print_char(int c);
int printf1(char *fmt, int iarg, char *sarg);
int my_strlen(char *s);

int main() {
    printf1("n=%d\n", 42, 0);
    printf1("s=%s\n", 0, "hello");
    printf1("c=%c\n", 65, 0);
    printf1("100%%\n", 0, 0);
    printf1("no format\n", 0, 0);
    return my_strlen("abcd");
}
