// 式の走査（残りのノード種別）— 単項マイナス・アドレス・減算・乗算・除算・剰余・以下。
// 各演算子の下に、その演算子でしか現れない文字列リテラルを置いてある。
// 二項演算子は左右で別の文字列にしてあるので、片側しか降りない走査もここで落ちる。
// 走査が枝を降りていないと、その文字列は .data に出ないままコンパイルが落ちる。
int main() {
    char *p;

    // Neg: 単項マイナスの operand
    if (-"neg"[0] != 0 - 'n') {
        return 1;
    }

    // Addr: & の operand
    p = &"addr"[1];
    if (*p != 'd') {
        return 2;
    }

    // Sub
    if ("sub_l"[4] - "sub_r"[4] != 'l' - 'r') {
        return 3;
    }

    // Mul
    if ("mul_l"[4] * "mul_r"[4] != 'l' * 'r') {
        return 4;
    }

    // Div
    if ("div_l"[4] / "div_r"[4] != 'l' / 'r') {
        return 5;
    }

    // Mod
    if ("mod_l"[4] % "mod_r"[4] != 'l' % 'r') {
        return 6;
    }

    // Le
    if ("le_l"[3] <= "le_r"[3]) {
        return 42;
    }
    return 7;
}
