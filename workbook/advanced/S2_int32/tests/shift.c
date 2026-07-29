// シフトも32bitで扱う
int main() {
    int x;
    x = 1;
    x = x << 31;         // int の符号ビットに届く
    if (x > 0) { return 1; }
    if (x != -2147483648) { return 2; }

    x = -8;
    if (x >> 1 != -4) { return 3; }      // 算術シフト

    return 3;
}
