// Package utils provides utility functions for the application.
package utils

import "strings"

// Capitalize returns a string with the first letter capitalized.
func Capitalize(s string) string {
    if len(s) == 0 {
        return s
    }
    return strings.ToUpper(s[:1]) + s[1:]
}
