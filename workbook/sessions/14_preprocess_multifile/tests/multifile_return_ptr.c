#include "return_ptr_lib.h"

int main() {
    struct Box a;
    a.value = 42;
    return identity(&a)->value;
}
