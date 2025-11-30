// Go module for testing function body optimization.
package main

import (
	"fmt"
	"strconv"
)

// User represents a user in the system
type User struct {
	ID    int
	Name  string
	Email string
}

// ProcessingResult contains valid and invalid users
type ProcessingResult struct {
	Valid   []User
	Invalid []User
}

// Calculator manages calculation history
type Calculator struct {
	name    string
	history []string
}

// NewCalculator creates a new calculator instance
func NewCalculator(name string) *Calculator {
	if name == "" {
		name = "default"
	}

	return &Calculator{
		name:    name,
		history: make([]string, 0),
	}
}

// Add performs addition and logs the result
func (c *Calculator) Add(a, b int) int {
	result := a + b
	entry := fmt.Sprintf("add(%d, %d) = %d", a, b, result)
	c.history = append(c.history, entry)
	fmt.Printf("Addition result: %d\n", result)
	return result
}

// Multiply performs multiplication and logs the result
func (c *Calculator) Multiply(a, b int) int {
	result := a * b
	entry := fmt.Sprintf("multiply(%d, %d) = %d", a, b, result)
	c.history = append(c.history, entry)
	return result
}

// GetHistory returns a copy of the calculation history
func (c *Calculator) GetHistory() []string {
	historyCopy := make([]string, len(c.history))
	copy(historyCopy, c.history)
	return historyCopy
}

func validateInput(value int) bool {
	str := strconv.Itoa(value)

	for _, ch := range str {
		if ch != '-' && (ch < '0' || ch > '9') {
			fmt.Fprintf(os.Stderr, "Input must be a number\n")
			return false
		}
	}

	if value == int(^uint(0)>>1) || value == -int(^uint(0)>>1)-1 {
		fmt.Fprintf(os.Stderr, "Input must be finite\n")
		return false
	}

	return true
}

// ProcessUserData validates and categorizes users
func ProcessUserData(users []User) *ProcessingResult {
	result := &ProcessingResult{
		Valid:   make([]User, 0),
		Invalid: make([]User, 0),
	}

	for _, user := range users {
		if user.ID > 0 && user.Name != "" && contains(user.Email, "@") {
			result.Valid = append(result.Valid, user)
		} else {
			result.Invalid = append(result.Invalid, user)
		}
	}

	return result
}

func contains(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

// ProcessArray applies a processor function to each item
func ProcessArray(items []interface{}, processor func(interface{}) interface{}) []interface{} {
	result := make([]interface{}, 0)

	for _, item := range items {
		if processor != nil {
			processed := processor(item)
			result = append(result, processed)
		}
	}

	return result
}

func main() {
	calc := NewCalculator("test")

	fmt.Println(calc.Add(2, 3))
	fmt.Println(calc.Multiply(4, 5))

	users := []User{
		{ID: 1, Name: "Alice", Email: "alice@example.com"},
		{ID: 2, Name: "Bob", Email: "bob@example.com"},
	}

	processed := ProcessUserData(users)
	fmt.Printf("Valid users: %d\n", len(processed.Valid))
}
