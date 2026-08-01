// 論理演算 ! && || — 結果は 0 か 1 の int。&& と || は短絡せず両辺を必ず評価する
int eval_count;

int bump(int v) {
    eval_count = eval_count + 1;
    return v;
}

int main() {
    int a;
    int b;
    a = 3;
    b = 0;

    if (!b != 1) {
        return 1;
    }
    if (!a != 0) {
        return 2;
    }
    if ((a && a) != 1) {
        return 3;
    }
    if ((a || b) != 1) {
        return 4;
    }
    if ((a && b) != 0) {
        return 5;
    }
    if ((b || b) != 0) {
        return 6;
    }

    eval_count = 0;
    if (bump(0) && bump(1)) {
        return 7;
    }
    if (bump(1) || bump(1)) {
        eval_count = eval_count + 0;
    }
    return eval_count * 10;
}
