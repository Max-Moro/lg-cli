/**
 * Utils header with function declarations.
 */

#ifndef UTILS_H
#define UTILS_H

struct Config {
    int value;
    char* name;
};

int initialize(struct Config* config);
void cleanup(struct Config* config);

#endif /* UTILS_H */
