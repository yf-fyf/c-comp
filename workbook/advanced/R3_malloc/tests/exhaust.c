// プールを使い切ったら 0(NULL)を返すことを確かめる
int heap_init(char *buf, int size);
char *my_malloc(int size);

int main() {
    char pool[512];
    char *p;
    int count;

    heap_init(pool, 512);
    count = 0;
    p = my_malloc(64);
    while (p != 0) {
        count = count + 1;
        if (count > 100) {
            return 99;      // 無限に確保できてしまっている
        }
        p = my_malloc(64);
    }
    return count;           // 確保できた個数(ヘッダのぶん 512/80 = 6 個)
}
