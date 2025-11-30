// Go module for testing public API filtering.
package main

import (
	"fmt"
	"strings"
	"time"
)

// Public module-level constants (should be preserved)
const PublicVersion = "1.0.0"
const APIEndpoint = "https://api.example.com"

// Private module-level constants (should be filtered out)
const privateSecret = "internal-use-only"

var internalConfig = struct {
	debug   bool
	verbose bool
}{
	debug:   true,
	verbose: false,
}

// User is a public structure (should be preserved)
type User struct {
	ID        int
	Name      string
	Email     string
	CreatedAt time.Time
}

// internalMetrics is a private structure (should be filtered out)
type internalMetrics struct {
	processTime int64
	memoryUsage int64
}

// UserRole is a public type alias (should be preserved)
type UserRole string

const (
	RoleAdmin UserRole = "admin"
	RoleUser  UserRole = "user"
	RoleGuest UserRole = "guest"
)

// internalEventType is a private type (should be filtered out)
type internalEventType string

const (
	eventUserCreated    internalEventType = "user_created"
	eventUserUpdated    internalEventType = "user_updated"
	eventCacheCleared   internalEventType = "cache_cleared"
)

// UserManager is a public class with mixed visibility members
type UserManager struct {
	// Public properties
	Version       string
	IsInitialized bool

	// Private properties (should be filtered out with public_api_only)
	internalCache map[string]*User
	metrics       *internalMetrics
	apiEndpoint   string
}

// NewUserManager is a public constructor (should be preserved)
func NewUserManager(apiEndpoint string) *UserManager {
	if apiEndpoint == "" {
		apiEndpoint = APIEndpoint
	}

	manager := &UserManager{
		Version:       PublicVersion,
		IsInitialized: false,
		internalCache: make(map[string]*User),
		metrics:       &internalMetrics{},
		apiEndpoint:   apiEndpoint,
	}

	manager.initialize()
	return manager
}

// CreateUser is a public method (should be preserved)
func (m *UserManager) CreateUser(name, email string) (*User, error) {
	if err := m.validateUserData(name, email); err != nil {
		return nil, err
	}

	user := &User{
		ID:        m.generateID(),
		Name:      name,
		Email:     email,
		CreatedAt: time.Now(),
	}

	m.internalCache[user.Email] = user
	return user, nil
}

// GetUserByID is a public method (should be preserved)
func (m *UserManager) GetUserByID(id int) *User {
	for _, user := range m.internalCache {
		if user.ID == id {
			return user
		}
	}

	return m.fetchUserFromAPI(id)
}

// GetAllUsers is a public method (should be preserved)
func (m *UserManager) GetAllUsers() []*User {
	users := make([]*User, 0, len(m.internalCache))
	for _, user := range m.internalCache {
		users = append(users, user)
	}
	return users
}

// validateUserData is a private method (should be filtered out)
func (m *UserManager) validateUserData(name, email string) error {
	if name == "" || email == "" {
		return fmt.Errorf("name and email are required")
	}

	if !m.isValidEmail(email) {
		return fmt.Errorf("invalid email format")
	}

	return nil
}

// generateID is a private method (should be filtered out)
func (m *UserManager) generateID() int {
	return int(time.Now().Unix())
}

// isValidEmail is a private method (should be filtered out)
func (m *UserManager) isValidEmail(email string) bool {
	return strings.Contains(email, "@") && strings.Contains(email, ".")
}

// fetchUserFromAPI is a private method (should be filtered out)
func (m *UserManager) fetchUserFromAPI(id int) *User {
	fmt.Printf("Fetching user %d from API\n", id)
	return nil
}

// initialize is a private method (should be filtered out)
func (m *UserManager) initialize() {
	m.IsInitialized = true
}

// logError is a private method (should be filtered out)
func (m *UserManager) logError(message string, err error) {
	fmt.Printf("[UserManager] %s: %v\n", message, err)
}

// ValidateUserRole is a public function (should be preserved)
func ValidateUserRole(role string) bool {
	validRoles := []UserRole{RoleAdmin, RoleUser, RoleGuest}
	for _, r := range validRoles {
		if string(r) == role {
			return true
		}
	}
	return false
}

// CreateDefaultUser is a public function (should be preserved)
func CreateDefaultUser() *User {
	return &User{
		ID:        0,
		Name:      "Default User",
		Email:     "default@example.com",
		CreatedAt: time.Now(),
	}
}

// formatInternalID is a private function (should be filtered out)
func formatInternalID(id int) string {
	return fmt.Sprintf("internal_%06d", id)
}

// internalLogger is a private structure (should be filtered out)
type internalLogger struct {
	logs []string
}

// newInternalLogger is a private constructor (should be filtered out)
func newInternalLogger() *internalLogger {
	return &internalLogger{
		logs: make([]string, 0),
	}
}

// log is a private method (should be filtered out)
func (l *internalLogger) log(message string) {
	timestamp := time.Now().Format(time.RFC3339)
	l.logs = append(l.logs, fmt.Sprintf("%s: %s", timestamp, message))
}

// getLogs is a private method (should be filtered out)
func (l *internalLogger) getLogs() []string {
	return l.logs
}

// clearLogs is a private method (should be filtered out)
func (l *internalLogger) clearLogs() {
	l.logs = make([]string, 0)
}

// UserUtils is a public namespace-like struct (should be preserved)
type UserUtils struct{}

// FormatUserName is a public method (should be preserved)
func (UserUtils) FormatUserName(user *User) string {
	return fmt.Sprintf("%s (%s)", user.Name, user.Email)
}

// GetUserAge is a public method (should be preserved)
func (UserUtils) GetUserAge(user *User) int64 {
	now := time.Now()
	return int64(now.Sub(user.CreatedAt).Hours() / 24)
}

// internalFormatting is a private function (should be filtered out)
func internalFormatting(text string) string {
	return strings.ToLower(strings.ReplaceAll(text, " ", "_"))
}

// InternalUtils is a private namespace-like struct (should be filtered out)
type InternalUtils struct{}

// debugLog is a private method (should be filtered out)
func (InternalUtils) debugLog(message string) {
	if internalConfig.debug {
		fmt.Printf("[Debug] %s\n", message)
	}
}

// measurePerformance is a private method (should be filtered out)
func (InternalUtils) measurePerformance(fn func()) {
	start := time.Now()
	fn()
	elapsed := time.Since(start)
	fmt.Printf("Performance: %v\n", elapsed)
}

func main() {
	manager := NewUserManager("")
	user, _ := manager.CreateUser("Test User", "test@example.com")
	fmt.Printf("Created user: %v\n", user)

	utils := UserUtils{}
	fmt.Println(utils.FormatUserName(user))
}
