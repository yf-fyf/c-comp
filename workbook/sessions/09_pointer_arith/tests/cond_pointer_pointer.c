int main() { int n; int *p; int **pp; n=42; p=&n; pp=&p; return **(0 ? 0 : pp); }
