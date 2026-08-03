int main() {
    int i;
    int j;
    int n;
    n = 0;
    i = 0;
    while (i < 3) {
        j = 0;
        while (j < 2) {
            n = n + 1;
            j = j + 1;
        }
        i = i + 1;
    }
    return n;
}
