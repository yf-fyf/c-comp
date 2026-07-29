int malloc(int size);

typedef struct Node {
    int val;
    struct Node *next;
} Node;

int main() {
    Node *n;
    n = malloc(sizeof(Node));
    n->val = 10;
    n->next = 0;
    return n->val;
}
