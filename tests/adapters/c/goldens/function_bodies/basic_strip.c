/**
 * C module for testing function body optimization.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    int id;
    char name[50];
    char email[100];
} User;

typedef struct {
    User* valid;
    User* invalid;
    int valid_count;
    int invalid_count;
} ProcessingResult;

typedef struct {
    char** history;
    int history_count;
    int history_capacity;
    char name[50];
} Calculator;

Calculator* calculator_new(const char* name) // … function body omitted (13 lines)

void calculator_free(Calculator* calc) // … function body omitted (9 lines)

int calculator_add(Calculator* calc, int a, int b) // … function body omitted (19 lines)

int calculator_multiply(Calculator* calc, int a, int b) // … function body omitted (18 lines)

char** calculator_get_history(Calculator* calc, int* count) {
    if (!calc || !count) {
        if (count) *count = 0;
        return NULL;
    }

    *count = calc->history_count;
    char** copy = (char**)malloc(calc->history_count * sizeof(char*));

    for (int i = 0; i < calc->history_count; i++) {
        copy[i] = strdup(calc->history[i]);
    }

    return copy;
}

static int validate_input(int value) // … function body omitted (18 lines)

ProcessingResult* process_user_data(User* users, int count) // … function body omitted (21 lines)

void free_processing_result(ProcessingResult* result) // … function body omitted (6 lines)

typedef void (*ItemProcessor)(void* item);

void** process_array(void** items, int count, ItemProcessor processor) {
    void** result = (void**)malloc(count * sizeof(void*));
    int result_count = 0;

    for (int i = 0; i < count; i++) {
        if (processor) {
            processor(items[i]);
            result[result_count++] = items[i];
        }
    }

    return result;
}

int main(void) // … function body omitted (23 lines)
