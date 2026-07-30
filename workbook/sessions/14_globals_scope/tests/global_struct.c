struct Pair {
    int a;
    int b;
};

struct Pair gp;

int sum_pair(struct Pair *p) {
    return p->a + p->b;
}

int main() {
    gp.a = 10;
    gp.b = 20;
    return sum_pair(&gp);
}
