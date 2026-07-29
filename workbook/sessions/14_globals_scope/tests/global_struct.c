typedef struct {
    int a;
    int b;
} Pair;

Pair gp;

int sum_pair(Pair *p) {
    return p->a + p->b;
}

int main() {
    gp.a = 10;
    gp.b = 20;
    return sum_pair(&gp);
}
