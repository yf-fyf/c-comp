// f15: 前処理 — #define 定数マクロをループ条件・更新に使用
#define LIMIT 10
#define STEP 3

int main() {
    int i;
    int count;
    count = 0;
    for (i = 0; i < LIMIT; i = i + STEP) {
        count = count + 1;
    }
    return count;
}
