int main() {
    int i;
    int sum;
    i = 1;
    sum = 0;
    while (1) {
        sum = sum + i;
        if (sum > 20) {
            break;
        }
        i = i + 1;
    }
    return i;
}
