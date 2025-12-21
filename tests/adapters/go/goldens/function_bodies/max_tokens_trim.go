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

	// … function body truncated (4 lines)
}

// Add performs addition and logs the result
func (c *Calculator) Add(a, b int) int {
	result := a + b
	// … method body truncated (4 lines)
}

// Multiply performs multiplication and logs the result
func (c *Calculator) Multiply(a, b int) int {
	result := a * b
	// … method body truncated (3 lines)
}

// GetHistory returns a copy of the calculation history
func (c *Calculator) GetHistory() []string {
	historyCopy := make([]string, len(c.history))
	copy(historyCopy, c.history)
	// … method body truncated
}

func validateInput(value int) bool {
	str := strconv.Itoa(value)

	for _, ch := range str {
	// … function body truncated (10 lines)
}

// ProcessUserData validates and categorizes users
func ProcessUserData(users []User) *ProcessingResult {
	result := &ProcessingResult{
		Valid:   make([]User, 0),
	// … function body truncated (10 lines)
}

func contains(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
	// … function body truncated (5 lines)
}

// ProcessArray applies a processor function to each item
func ProcessArray(items []interface{}, processor func(interface{}) interface{}) []interface{} {
	result := make([]interface{}, 0)

	for _, item := range items {
	// … function body truncated (6 lines)
}

func main() {
	calc := NewCalculator("test")

	// … function body truncated (8 lines)
}
