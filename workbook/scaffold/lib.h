/* lib.h — 標準ライブラリ宣言（教員提供スキャフォールド）
 *
 * 宣言のみ。実体はリンク時に libc から解決する。
 * コマ 11 以降で #include "lib.h" して使用する。
 */

/* 不完全型（FILE * として使う型を先に定義する） */
typedef struct _IO_FILE FILE;

/* 出力 */
int printf(char *fmt, ...);
int fprintf(FILE *f, char *fmt, ...);

/* ファイル入力 */
FILE *fopen(char *path, char *mode);
int   fread(void *buf, int size, int n, FILE *f);
int   fclose(FILE *f);

/* メモリ */
void *malloc(int size);         /* 戻り値は任意の T * へ暗黙変換 */

/* プロセス */
void exit(int code);

/* 文字列 */
int   strcmp(char *a, char *b);
int   strlen(char *s);
char *strchr(char *s, int c);

/* 定数 */
#define NULL 0
