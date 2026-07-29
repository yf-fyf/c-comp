// 右辺が評価されなかったことを、副作用の有無で確かめる
int counter;

int bump() {
    counter = counter + 1;
    return 1;
}

int main() {
    counter = 0;
    if (0 && bump()) { return 90; }      // bump は呼ばれないはず
    if (counter != 0) { return 91; }

    if (1 || bump()) { }                 // bump は呼ばれないはず
    if (counter != 0) { return 92; }

    if (1 && bump()) { }                 // ここでは呼ばれる
    if (counter != 1) { return 93; }

    return counter;                      // 1
}
