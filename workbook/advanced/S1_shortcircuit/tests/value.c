// && と || が返す値そのものを確かめる(1 か 0)
int main() {
    int a;
    a = 0;
    if ((1 && 1) != 1) { return 1; }
    if ((1 && 0) != 0) { return 2; }
    if ((0 && 1) != 0) { return 3; }
    if ((5 && 3) != 1) { return 4; }     // 非0同士は 1
    if ((0 || 0) != 0) { return 5; }
    if ((0 || 7) != 1) { return 6; }     // 非0は 1 に正規化
    if ((2 || 3) != 1) { return 7; }
    a = 1 && 1 && 0;
    if (a != 0) { return 8; }
    a = 0 || 0 || 4;
    if (a != 1) { return 9; }
    return 42;
}
