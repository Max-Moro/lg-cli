/**
 * C++ module for testing include optimization.
 */

// Standard library includes (external)
#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <set>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <functional>
#include <memory>
#include <utility>
#include <cmath>
#include <ctime>
#include <cstdlib>

// More standard library
#include <fstream>
#include <sstream>
#include <iomanip>
#include <exception>
#include <stdexcept>
#include <type_traits>
#include <chrono>
#include <thread>
#include <mutex>
#include <condition_variable>

// Third-party library includes (external)
#include <boost/algorithm/string.hpp>
#include <boost/filesystem.hpp>
#include <boost/thread.hpp>
#include <boost/asio.hpp>
#include <boost/beast.hpp>

#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <fmt/format.h>
#include <fmt/chrono.h>

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <curl/curl.h>
#include <sqlite3.h>
#include <pcre.h>

// Local/project includes (should be considered local)
// … 9 imports omitted

// Relative includes with different depth levels
// … 3 imports omitted

// Long include lists from single directory (candidates for summarization)
// … 23 imports omitted

class ImportTestService {
private:
    void* userService;
    void* dbConnection;
    void* logger;

public:
    ImportTestService(void* userService, void* dbConnection, void* logger)
        : userService(userService)
        , dbConnection(dbConnection)
        , logger(logger) {}

    std::vector<std::map<std::string, std::string>> processData(
        const std::vector<void*>& data
    ) {
        // Using standard library
        std::vector<std::map<std::string, std::string>> processed;

        for (const auto& item : data) {
            std::map<std::string, std::string> result;
            // Using boost for string operations
            std::string timestamp = boost::algorithm::to_upper_copy(std::string("test"));
            result["timestamp"] = timestamp;
            processed.push_back(result);
        }

        // Using local utilities (would call validation functions here)
        return processed;
    }

    std::string makeHttpRequest(const std::string& url) {
        try {
            // Using libcurl
            CURL* curl = curl_easy_init();
            if (!curl) {
                throw std::runtime_error("Failed to initialize curl");
            }

            curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
            curl_easy_setopt(curl, CURLOPT_TIMEOUT, 5L);
            curl_easy_setopt(curl, CURLOPT_USERAGENT, "ImportTestService/1.0");

            CURLcode res = curl_easy_perform(curl);
            curl_easy_cleanup(curl);

            if (res != CURLE_OK) {
                throw std::runtime_error(curl_easy_strerror(res));
            }

            return "success";
        } catch (const std::exception& e) {
            std::cerr << "HTTP request failed: " << e.what() << std::endl;
            throw;
        }
    }

    std::string serializeData(const void* data) {
        // Using nlohmann::json
        nlohmann::json jobj;
        jobj["data"] = "test";

        return jobj.dump();
    }

    int queryDatabase(const std::string& sql) {
        // Using SQLite
        sqlite3* conn = nullptr;
        if (!conn) {
            throw std::runtime_error("Database connection failed");
        }

        char* errMsg = nullptr;
        int rc = sqlite3_exec(conn, sql.c_str(), nullptr, nullptr, &errMsg);

        if (rc != SQLITE_OK) {
            std::string error = errMsg;
            sqlite3_free(errMsg);
            throw std::runtime_error(error);
        }

        return 0;
    }
};

// Forward declarations (should not be treated as includes)
class User;
class Service;
namespace detail {
    class Impl;
}

std::unique_ptr<User> createUser();
