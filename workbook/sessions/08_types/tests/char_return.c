char narrow(int n) { return n; }
char add_one(int n) { return n+1; }
int main() { return (narrow(300)==44) + (narrow(255)==-1) + (narrow(-129)==127) + (add_one(127)==-128); }
