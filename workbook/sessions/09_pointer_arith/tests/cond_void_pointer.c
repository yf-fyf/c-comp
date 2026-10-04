int main() { int n; int *p; void *v; int *q; n=42; p=&n; v=p; q=0 ? v : p; return *q; }
