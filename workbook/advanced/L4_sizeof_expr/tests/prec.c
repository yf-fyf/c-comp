// 優先順位 — sizeof は単項演算子。sizeof x + 1 は (sizeof x) + 1
int main() {
    int a;
    char c;
    int r;

    a = 0;
    c = 0;

    // sizeof (c + 1) と読まれると 4 になってしまう。(sizeof c) + 1 なら 2
    if (sizeof c + 1 != 2) { return 1; }
    if (sizeof a + 1 != 5) { return 2; }

    // 乗除も sizeof より弱い
    if (sizeof a * 2 != 8) { return 3; }
    if (sizeof c * 3 != 3) { return 4; }

    // 左から来ても同じ
    if (1 + sizeof c != 2) { return 5; }

    // 括弧をつけた式形式でも変わらない
    if (sizeof (c) + 1 != 2) { return 6; }

    // 単独の値として使える
    r = sizeof c;
    if (r != 1) { return 7; }

    // 単項 - との組み合わせ(sizeof は -a を丸ごと取る)
    if (sizeof -a != 4) { return 8; }

    return 42;
}
