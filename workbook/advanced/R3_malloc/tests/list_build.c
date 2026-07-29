// 自前 malloc で連結リストを作って走査する(コマ13 の再現)
int heap_init(char *buf, int size);
char *my_malloc(int size);

typedef struct Node {
    int val;
    struct Node *next;
} Node;

int main() {
    char pool[1024];
    Node *head;
    Node *n;
    int sum;
    int i;

    heap_init(pool, 1024);
    head = 0;
    for (i = 1; i <= 3; i = i + 1) {
        n = my_malloc(sizeof(Node));
        n->val = i * 10;
        n->next = head;
        head = n;
    }
    sum = 0;
    while (head != 0) {
        sum = sum + head->val;
        head = head->next;
    }
    return sum;
}
