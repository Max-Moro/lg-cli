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

Calculator* calculator_new(const char* name) {
    Calculator* calc = (Calculator*)malloc(sizeof(Calculator));
    if (!calc) return NULL;

    strncpy(calc->name, name ? name : "default", sizeof(calc->name) - 1);
    calc->name[sizeof(calc->name) - 1] = '\0';

    calc->history_capacity = 10;
    calc->history = (char**)malloc(calc->history_capacity * sizeof(char*));
    calc->history_count = 0;

    return calc;
}

void calculator_free(Calculator* calc) {
    if (!calc) return;

    for (int i = 0; i < calc->history_count; i++) {
        free(calc->history[i]);
    }
    free(calc->history);
    free(calc);
}

int calculator_add(Calculator* calc, int a, int b) {
    if (!calc) return 0;

    int result = a + b;

    char buffer[100];
    snprintf(buffer, sizeof(buffer), "add(%d, %d) = %d", a, b, result);

    if (calc->history_count >= calc->history_capacity) {
        calc->history_capacity *= 2;
        calc->history = (char**)realloc(calc->history,
                                       calc->history_capacity * sizeof(char*));
    }

    calc->history[calc->history_count++] = strdup(buffer);
    printf("Addition result: %d\n", result);

    return result;
}

int calculator_multiply(Calculator* calc, int a, int b) {
    if (!calc) return 0;

    int result = a * b;

    char buffer[100];
    snprintf(buffer, sizeof(buffer), "multiply(%d, %d) = %d", a, b, result);

    if (calc->history_count >= calc->history_capacity) {
        calc->history_capacity *= 2;
        calc->history = (char**)realloc(calc->history,
                                       calc->history_capacity * sizeof(char*));
    }

    calc->history[calc->history_count++] = strdup(buffer);

    return result;
}

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

static int validate_input(int value) {
    char buffer[20];
    snprintf(buffer, sizeof(buffer), "%d", value);

    for (int i = 0; buffer[i]; i++) {
        if (buffer[i] != '-' && (buffer[i] < '0' || buffer[i] > '9')) {
            fprintf(stderr, "Input must be a number\n");
            return 0;
        }
    }

    if (value == INT_MAX || value == INT_MIN) {
        fprintf(stderr, "Input must be finite\n");
        return 0;
    }

    return 1;
}

ProcessingResult* process_user_data(User* users, int count) {
    ProcessingResult* result = (ProcessingResult*)malloc(sizeof(ProcessingResult));
    if (!result) return NULL;

    result->valid = (User*)malloc(count * sizeof(User));
    result->invalid = (User*)malloc(count * sizeof(User));
    result->valid_count = 0;
    result->invalid_count = 0;

    for (int i = 0; i < count; i++) {
        if (users[i].id > 0 &&
            strlen(users[i].name) > 0 &&
            strchr(users[i].email, '@') != NULL) {
            result->valid[result->valid_count++] = users[i];
        } else {
            result->invalid[result->invalid_count++] = users[i];
        }
    }

    return result;
}

void free_processing_result(ProcessingResult* result) {
    if (!result) return;
    free(result->valid);
    free(result->invalid);
    free(result);
}

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

int main(void) {
    Calculator* calc = calculator_new("test");
    if (!calc) {
        fprintf(stderr, "Failed to create calculator\n");
        return 1;
    }

    printf("%d\n", calculator_add(calc, 2, 3));
    printf("%d\n", calculator_multiply(calc, 4, 5));

    User users[2] = {
        {1, "Alice", "alice@example.com"},
        {2, "Bob", "bob@example.com"}
    };

    ProcessingResult* processed = process_user_data(users, 2);
    printf("Valid users: %d\n", processed->valid_count);

    free_processing_result(processed);
    calculator_free(calc);

    return 0;
}
