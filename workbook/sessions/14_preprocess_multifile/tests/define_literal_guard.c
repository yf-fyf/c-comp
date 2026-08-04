// define_literal_guard: マクロ置換は文字列・文字リテラル・コメントの中身を変えない
#include "lib.h"

#define N 7

int main() {
    int Ncount;
    // N ← 行コメント内の N は置換されない
    printf("N\n");        // 文字列リテラル "N" もそのまま出力される
    Ncount = 'N';         // 文字リテラル 'N'（= 78）もそのまま
    return Ncount - N;    // 78 - 7 = 71
}
