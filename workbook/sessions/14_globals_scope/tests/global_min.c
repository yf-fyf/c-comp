int total;

int add(int x) {
    total = total + x;
    return total;
}

int main() {
    total = 0;
    add(10);
    add(20);
    return total;
}
