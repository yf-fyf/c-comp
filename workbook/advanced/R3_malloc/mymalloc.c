// R3: 自前 malloc(スケルトン)
//
// ヒープは呼び出し側から渡された領域(プール)を使う。
// ブロックの前に「管理用のヘッダ」を置き、解放済みブロックを再利用する。
//
//   [ヘッダ][ユーザ領域 size B][ヘッダ][ユーザ領域 ...] ... [未使用領域]
//                                                          ^ heap_brk
//
// 実装する順番:
//   Step 1: align8 / heap_init / my_malloc(切り出しだけ)
//   Step 2: my_free / find_free(再利用)
//   Step 3: heap_used
//
// 確認:
//   python3 check.py

struct Header {
    int size;               // このブロックのユーザ領域のバイト数
    int free;               // 1 なら解放済み
    struct Header *next;    // 次のブロックのヘッダ(管理用リスト)
};

struct Header *heap_head;      // 管理リストの先頭
char   *heap_limit;     // プールの終端
char   *heap_brk;       // まだ切り出していない領域の先頭

// ---- Step 1: 8 バイト境界へ切り上げる ----
// 例: 1..8 → 8、9..16 → 16
int align8(int n) {
    return 0;   // TODO(Step 1)
}

// ---- Step 1: プールを受け取って初期化する ----
// heap_head を 0、heap_brk を buf、heap_limit を buf + size にする。
int heap_init(char *buf, int size) {
    // TODO(Step 1)
    return 0;
}

// ---- Step 2: 再利用できるブロックを探す(first fit) ----
// 管理リストを先頭からたどり、free == 1 かつ size 以上のものを返す。
// 見つからなければ 0 を返す。
struct Header *find_free(int size) {
    struct Header *h;
    // TODO(Step 2)
    return 0;
}

// ---- Step 1(切り出し)+ Step 2(再利用) ----
//
// 方針:
//   1. size を align8 で切り上げる
//   2. find_free で再利用できるブロックを探す。あれば free = 0 にして
//      「ヘッダの次のアドレス」を返す
//      (cp = h; return cp + sizeof(struct Header); と書く。Core プロファイルに
//       キャストはないので、いったん char * の変数に入れる)
//   3. なければ未使用領域から切り出す
//      - heap_brk + sizeof(struct Header) + size が heap_limit を超えるなら 0 を返す
//      - p = heap_brk とし、heap_brk を進める
//      - p をヘッダとして size / free = 0 / next = heap_head を設定し、
//        heap_head を更新する
//      - p + sizeof(struct Header) を返す
char *my_malloc(int size) {
    struct Header *h;
    char *p;
    char *cp;
    // TODO(Step 1, Step 2)
    return 0;
}

// ---- Step 2: 解放する ----
// ユーザ領域のアドレスから sizeof(struct Header) 引くとヘッダに戻れる。
// そのヘッダの free を 1 にするだけでよい(領域は返さない)。
int my_free(char *p) {
    struct Header *h;
    // TODO(Step 2)
    return 0;
}

// ---- Step 3: 確保済み(未解放)のバイト数を返す ----
// 管理リストをたどり、free == 0 のブロックの size を足す。
int heap_used() {
    struct Header *h;
    int total;
    // TODO(Step 3)
    return 0;
}
