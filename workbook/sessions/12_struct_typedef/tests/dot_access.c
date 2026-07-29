typedef struct {
    int x;
    int y;
} Point;

int main() {
    Point p;
    p.x = 3;
    p.y = 4;
    return p.x + p.y;
}
