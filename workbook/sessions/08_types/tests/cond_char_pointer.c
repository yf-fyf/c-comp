int main() { char c; char *p; c=-1; p=&c; return (*(0 ? 0 : p)==-1) + (*(1 ? p : 0)==-1); }
