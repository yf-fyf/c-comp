#include "lib.h"
int main() { int *p; p=malloc(12); p[0]=10; p[1]=20; p[2]=30; return *((0 ? 0 : p)+1) + *((1 ? p : 0)+2); }
