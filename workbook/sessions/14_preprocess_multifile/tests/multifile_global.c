#include "stat_lib.h"

int main() {
    reset_stats();
    add_stat(10);
    add_stat(20);
    add_stat(30);
    return get_count() + get_total();
}
