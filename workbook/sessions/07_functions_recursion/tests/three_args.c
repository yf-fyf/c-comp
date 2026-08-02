int clamp(int val, int lo, int hi) {
    if (val < lo) {
        return lo;
    }
    if (val > hi) {
        return hi;
    }
    return val;
}

int main() {
    return clamp(15, 0, 10) + clamp(-3, 0, 10) + clamp(5, 0, 10);
}
