// lib.h — 標準ライブラリ宣言（教員提供スキャフォールド）
//
// 宣言のみ。実体はリンク時に libc から解決する。
// コマ9以降で #include "lib.h" して使用する。

// 不透明型。FILE * としてのみ使う（完全化しない）
struct FILE;

// 出力
int printf(char *fmt, ...);
int fprintf(struct FILE *f, char *fmt, ...);

// ストリーム
struct FILE *fdopen(int fd, char *mode);
struct FILE *fopen(char *path, char *mode);
int fread(void *buf, int size, int n, struct FILE *f);
int fclose(struct FILE *f);

// メモリ
void *malloc(int size);

// プロセス
void exit(int code);

// 定数
#define NULL 0
