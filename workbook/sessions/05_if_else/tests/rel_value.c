// 比較・等値演算子の結果は int の 0 か 1 である（条件式の中だけでなく値としても使える）
int main() {
    int t;
    int f;
    t = 3 < 5;
    f = 5 < 3;
    if (t != 1) {
        return 1;
    }
    if (f != 0) {
        return 2;
    }
    if ((3 <= 3) != 1) {
        return 3;
    }
    if ((3 > 5) != 0) {
        return 4;
    }
    if ((3 >= 3) != 1) {
        return 5;
    }
    if ((3 == 3) != 1) {
        return 6;
    }
    if ((3 != 3) != 0) {
        return 7;
    }
    return t + f + 40;
}
