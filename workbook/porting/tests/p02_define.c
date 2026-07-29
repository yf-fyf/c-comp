#define START 1
#define STOP 10
#define STEP 2

int main() {
    int i;
    int sum;
    sum = 0;
    for (i = START; i <= STOP; i = i + STEP) {
        sum = sum + i;
    }
    return sum;
}
