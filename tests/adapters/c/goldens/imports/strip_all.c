/**
 * C module for testing include optimization.
 */

// Standard library includes (external)
// … 12 imports omitted

// POSIX headers (external/system)
// … 8 imports omitted

// Common external libraries (external)
// … 8 imports omitted

// Local/project includes (should be considered local)
// … 9 imports omitted

// Relative includes with different depth levels
// … 3 imports omitted

// Long include lists from single directory (candidates for summarization)
// … 23 imports omitted

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
