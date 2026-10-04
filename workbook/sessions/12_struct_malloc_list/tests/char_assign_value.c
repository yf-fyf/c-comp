struct Byte { char c; };
int main() { struct Byte s; return (s.c=255)==-1; }
