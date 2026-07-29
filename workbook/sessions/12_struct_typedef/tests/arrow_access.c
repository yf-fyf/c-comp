typedef struct {
    int x;
    int y;
} Point;

int distance_sq(Point *p) {
    return p->x * p->x + p->y * p->y;
}

int main() {
    Point p;
    p.x = 3;
    p.y = 4;
    return distance_sq(&p);
}
