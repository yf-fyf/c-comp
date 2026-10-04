int yes(char *s) { return *s != 0; }
int main() { return yes("left") || yes("right"); }
