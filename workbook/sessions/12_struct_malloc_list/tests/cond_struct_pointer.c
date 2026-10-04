struct Pair { char c; int n; };
int main() { struct Pair s; s.c=1; s.n=42; return (0 ? 0 : &s)->n; }
