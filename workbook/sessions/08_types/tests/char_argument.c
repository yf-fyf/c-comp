int fixed(char c, int n) { return (c==-1) + (n==300); }
char forward(char c) { return c; }
int main() { return fixed(255,300) + (forward(300)==44); }
