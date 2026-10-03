char *identity(char *p) {
    return p;
}

int main() {
    char *p;
    p = identity("ab");
    // char * を返す呼出しを直接参照すると、lb で1文字だけ読む。
    return *identity(p) == 'a';
}
