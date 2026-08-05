// sizeof(void *) — void * の導入はコマ12（feature map）。翻訳時定数として正しいサイズが出るか確認する。
int main() {
    if (sizeof(void *) != 8) {
        return 1;
    }
    return 8;
}
