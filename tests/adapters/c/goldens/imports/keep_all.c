/**
 * C module for testing include optimization.
 */

// Standard library includes (external)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <limits.h>
#include <float.h>
#include <math.h>
#include <time.h>
#include <errno.h>
#include <assert.h>

// POSIX headers (external/system)
#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <pthread.h>
#include <signal.h>
#include <dirent.h>

// Common external libraries (external)
#include <zlib.h>
#include <curl/curl.h>
#include <sqlite3.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <libpq-fe.h>
#include <json-c/json.h>
#include <pcre.h>

// Local/project includes (should be considered local)
#include "services/user_service.h"
#include "database/connection.h"
#include "errors/validation_error.h"
#include "errors/network_error.h"
#include "utils/helpers/date_formatter.h"
#include "utils/helpers/json_parser.h"
#include "types/api_response.h"
#include "types/user_model.h"
#include "types/post_model.h"

// Relative includes with different depth levels
#include "../shared/utilities.h"
#include "../../core/core_module.h"
#include "../../../config/app_config.h"

// Long include lists from single directory (candidates for summarization)
#include "validation/email_validator.h"
#include "validation/password_validator.h"
#include "validation/phone_validator.h"
#include "validation/postal_code_validator.h"
#include "validation/credit_card_validator.h"
#include "validation/input_sanitizer.h"
#include "validation/currency_formatter.h"
#include "validation/phone_formatter.h"
#include "validation/slug_generator.h"
#include "validation/hash_creator.h"
#include "validation/hash_verifier.h"

#include "operations/create_user.h"
#include "operations/update_user.h"
#include "operations/delete_user.h"
#include "operations/get_user_by_id.h"
#include "operations/get_user_by_email.h"
#include "operations/get_users_by_role.h"
#include "operations/get_users_with_pagination.h"
#include "operations/activate_user.h"
#include "operations/deactivate_user.h"
#include "operations/reset_user_password.h"
#include "operations/change_user_role.h"
#include "operations/validate_user_permissions.h"

typedef struct {
    void* user_service;
    void* db_connection;
    void* logger;
} ImportTestService;

ImportTestService* import_test_service_new(
    void* user_service,
    void* db_connection,
    void* logger
) {
    ImportTestService* service = (ImportTestService*)malloc(sizeof(ImportTestService));
    if (!service) return NULL;

    service->user_service = user_service;
    service->db_connection = db_connection;
    service->logger = logger;

    return service;
}

void* process_data(ImportTestService* service, void** data, int count) {
    if (!service || !data) return NULL;

    // Using external libraries (zlib for compression)
    z_stream stream;
    memset(&stream, 0, sizeof(stream));

    // Using standard library functions
    time_t now = time(NULL);
    struct tm* timeinfo = localtime(&now);

    // Using POSIX functions
    pid_t pid = getpid();

    // Using local utilities
    // (would call validation functions here)

    return NULL;
}

int make_http_request(ImportTestService* service, const char* url) {
    if (!service || !url) return -1;

    // Using libcurl
    CURL* curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "Failed to initialize curl\n");
        return -1;
    }

    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 5L);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "ImportTestService/1.0");

    CURLcode res = curl_easy_perform(curl);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK) {
        fprintf(stderr, "HTTP request failed: %s\n", curl_easy_strerror(res));
        return -1;
    }

    return 0;
}

char* serialize_data(void* data) {
    if (!data) return NULL;

    // Using json-c
    json_object* jobj = json_object_new_object();
    if (!jobj) return NULL;

    // Add data to JSON object
    json_object_object_add(jobj, "data", json_object_new_string("test"));

    const char* json_str = json_object_to_json_string(jobj);
    char* result = strdup(json_str);

    json_object_put(jobj);
    return result;
}

int query_database(ImportTestService* service, const char* sql) {
    if (!service || !sql) return -1;

    // Using libpq (PostgreSQL)
    PGconn* conn = NULL; // Would connect here
    if (!conn) {
        fprintf(stderr, "Database connection failed\n");
        return -1;
    }

    PGresult* res = PQexec(conn, sql);
    if (PQresultStatus(res) != PGRES_TUPLES_OK) {
        fprintf(stderr, "Query failed: %s\n", PQerrorMessage(conn));
        PQclear(res);
        return -1;
    }

    int rows = PQntuples(res);
    PQclear(res);

    return rows;
}

void free_import_test_service(ImportTestService* service) {
    if (!service) return;
    free(service);
}
