// sizeof 式 — 型名形式と同じ値になる
struct Point {
    int x;
    int y;
};

int main() {
    int a;
    char c;
    int *p;
    char *s;
    struct Point pt;
    struct Point *pp;

    a = 1;
    c = 65;

    // 変数
    if (sizeof a != sizeof(int)) { return 1; }
    if (sizeof c != sizeof(char)) { return 2; }
    if (sizeof p != sizeof(int*)) { return 3; }
    if (sizeof s != sizeof(char*)) { return 4; }
    if (sizeof pt != sizeof(struct Point)) { return 5; }

    // 間接参照 — 指す先の型のサイズ
    p = &a;
    s = &c;
    if (sizeof *p != sizeof(int)) { return 6; }
    if (sizeof *s != sizeof(char)) { return 7; }

    // 添字・メンバ
    if (sizeof p[0] != sizeof(int)) { return 8; }
    pp = &pt;
    if (sizeof *pp != sizeof(struct Point)) { return 9; }
    if (sizeof pt.x != sizeof(int)) { return 10; }
    if (sizeof pp->y != sizeof(int)) { return 11; }

    // アドレス取得
    if (sizeof &a != sizeof(int*)) { return 12; }
    if (sizeof &c != sizeof(char*)) { return 13; }

    // 括弧つきの式
    if (sizeof (a + 1) != sizeof(int)) { return 14; }
    if (sizeof (c) != sizeof(char)) { return 15; }

    // ポインタ演算の結果はポインタ型
    if (sizeof (p + 1) != sizeof(int*)) { return 16; }

    // sizeof 自身の結果は int
    if (sizeof sizeof a != sizeof(int)) { return 17; }

    // 文字列リテラルは char*
    if (sizeof "abc" != sizeof(char*)) { return 18; }

    return 42;
}
