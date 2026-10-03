// プロトタイプから、関数呼出しが int * を返すと分かる。
int *identity(int *p);

int main() {
    int x;
    x = 42;
    return *identity(&x);
}

int *identity(int *p) {
    return p;
}
