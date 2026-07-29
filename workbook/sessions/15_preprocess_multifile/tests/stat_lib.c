int count;
int total;

void reset_stats() {
    count = 0;
    total = 0;
}

void add_stat(int val) {
    total = total + val;
    count = count + 1;
}

int get_count() {
    return count;
}

int get_total() {
    return total;
}
