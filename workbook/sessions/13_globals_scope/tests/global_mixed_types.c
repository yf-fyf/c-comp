struct Mixed { char c; int n; int *p; };
char gc; int gi; int *gp; struct Mixed gs;
int main() { if (gc || gi || gp || gs.c || gs.n || gs.p) return 1; gi=42; gp=&gi; gs.p=gp; return *gs.p; }
