int add(int a, int b) {
    return a + b;
}

int mul(int a, int b) {
    int i;
    int result;
    result = 0;
    for (i = 0; i < b; i = i + 1) {
        result = add(result, a);
    }
    return result;
}

int main() {
    return mul(6, 7);
}
