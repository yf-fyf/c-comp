// lib.h のストリーム関数 — fdopen / fprintf / fopen / fread / fclose
// 読み出し先には Linux に必ずある /dev/zero を使う（読むと 0 が返る）。
#include "lib.h"

int main() {
    struct FILE *err;
    struct FILE *f;
    int *buf;
    int n;

    err = fdopen(2, "w");
    fprintf(err, "file_stream: start\n");

    f = fopen("no_such_file_in_this_directory", "r");
    if (f != NULL) {
        return 1;
    }

    f = fopen("/dev/zero", "r");
    if (f == NULL) {
        return 2;
    }

    buf = malloc(sizeof(int));
    buf[0] = 12345;
    n = fread(buf, sizeof(int), 1, f);
    if (n != 1) {
        return 3;
    }
    if (buf[0] != 0) {
        return 4;
    }
    if (fclose(f) != 0) {
        return 5;
    }

    printf("stream ok\n");
    return 42;
}
