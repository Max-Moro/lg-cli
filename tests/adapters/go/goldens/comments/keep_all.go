// Go module for testing comment optimization.
//
// This module contains various types of comments to test
// different comment processing policies and edge cases.
package main

import (
	"fmt"
	"regexp"
	"time"
)

// Single-line comment at module level
const ModuleVersion = "1.0.0" // TODO: Move to config file

// User represents a user with documentation comments.
// This should be preserved when keeping documentation comments.
type User struct {
	ID      int    // User identifier
	Name    string // FIXME: Should validate name format
	Email   string // User's email address
	Profile *Profile // Optional profile data
}

// Profile contains user profile information
type Profile struct {
	Bio    string
	Avatar string
}

// CommentedService provides various operations with extensive comments
type CommentedService struct {
	config interface{} // Service configuration
	logger interface{} // Optional logger
}

// NewCommentedService creates a new service instance with detailed documentation.
//
// Initializes the service with the provided configuration
// and sets up the logging system if logger is provided.
func NewCommentedService(config, logger interface{}) *CommentedService {
	service := &CommentedService{
		config: config,
		logger: logger,
	}

	// Initialize service
	// (implementation details here)

	// TODO: Add configuration validation
	// FIXME: Logger should be required, not optional

	return service
}

// ProcessUser processes user data with validation.
//
// This function performs comprehensive user data processing including
// validation, transformation, and persistence operations. It handles
// various edge cases and provides detailed error reporting.
func ProcessUser(userData *User) (*User, error) {
	// Pre-processing validation
	if userData == nil {
		return nil, fmt.Errorf("user data is required")
	}

	/*
	 * Multi-line comment explaining
	 * the validation logic that follows.
	 * This is important business logic.
	 */
	validationResult := validateUser(userData)
	if !validationResult.IsValid {
		// Log validation failure
		fmt.Printf("Validation failed: %v\n", validationResult.Errors)
		return nil, fmt.Errorf("validation failed")
	}

	// Transform data for storage
	transformed := transformUserData(userData)

	// Persist to database
	// NOTE: This could be optimized with batch operations
	saved, err := saveUser(transformed)
	if err != nil {
		return nil, err
	}

	return saved, nil // Return the saved user
}

func validateUser(userData *User) ValidationResult {
	// Simple validation logic
	errors := make([]string, 0)

	// Check required fields
	if userData.Name == "" {
		errors = append(errors, "Name is required") // Error message
	}

	if userData.Email == "" {
		errors = append(errors, "Email is required")
	}

	// Validate email format
	// Regular expression for email validation
	emailRegex := regexp.MustCompile(`^[^\s@]+@[^\s@]+\.[^\s@]+$`)
	if userData.Email != "" && !emailRegex.MatchString(userData.Email) {
		errors = append(errors, "Invalid email format")
	}

	return ValidationResult{
		IsValid: len(errors) == 0,
		Errors:  errors,
	}
}

// Private helper method
func transformUserData(userData *User) *User {
	/*
	 * Data transformation logic.
	 * Convert partial user data to complete user object
	 * with all required fields populated.
	 */
	return &User{
		ID:    generateUserID(),           // Generate unique ID
		Name:  trimString(userData.Name),  // Clean up name
		Email: toLowerCase(userData.Email), // Normalize email
		Profile: userData.Profile,          // Default profile
	}
}

// generateUserID generates unique user ID.
func generateUserID() int {
	// Simple ID generation
	return int(time.Now().Unix())
}

// TODO: Implement proper persistence layer
func saveUser(user *User) (*User, error) {
	// Simulate database save
	// In real implementation, this would use a database

	// Log save operation
	if user != nil {
		fmt.Printf("Saving user: %d\n", user.ID)
	}

	// Simulate async operation
	// (sleep or similar in real code)

	return user, nil // Return saved user
}

// ProcessString is a utility function with comprehensive documentation.
//
// It processes the input string according to specific rules.
func ProcessString(input string) string {
	// Input validation
	if input == "" {
		return "" // Return empty string for invalid input
	}

	/* Process the string:
	 * 1. Trim whitespace
	 * 2. Convert to lowercase
	 * 3. Remove special characters
	 */
	trimmed := trimString(input)
	lowercase := toLowerCase(trimmed)
	cleaned := removeSpecialChars(lowercase)

	return cleaned // Return processed string
}

// Module-level function without documentation
func undocumentedHelper() {
	// This function has no documentation comments
	// Only regular comments explaining implementation

	// Implementation details...
	data := "helper data"

	// Process data
	fmt.Println(data) // Log the data
}

// ValidationResult holds validation results
type ValidationResult struct {
	IsValid bool     // Whether validation passed
	Errors  []string // List of validation errors
}

// ServiceConfig holds service configuration
type ServiceConfig struct {
	Timeout int    // Request timeout in milliseconds
	Retries int    // Number of retry attempts
	BaseURL string // Base URL for API calls
}

/*
 * DefaultConfig is the default configuration
 * This is used when no custom config is provided
 */
var DefaultConfig = ServiceConfig{
	Timeout: 5000,                    // 5 second timeout
	Retries: 3,                       // 3 retry attempts
	BaseURL: "http://localhost:3000", // Default base URL
}

func trimString(s string) string     { return s }
func toLowerCase(s string) string    { return s }
func removeSpecialChars(s string) string { return s }
