// print_int が境界値を正しく出せるか
int print_int(int n);
int print_str(char *s);

int main() {
    print_int(0);      print_str("\n");
    print_int(7);      print_str("\n");
    print_int(-1234);  print_str("\n");
    print_int(1000000); print_str("\n");
    return 0;
}
