// 引き算でも桁あふれが正しく折り返す(INT_MIN をまたぐ)
int main() {
    int x;
    x = -2147483647;
    x = x - 2;            // INT_MIN をまたいで折り返す
    if (x < 0) { return 1; }
    if (x != 2147483647) { return 2; }

    return 3;
}
