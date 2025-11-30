// Go module for testing import optimization.
package main

// Standard library imports (external)
import (
	"bufio"
	"bytes"
	"context"
	"crypto/md5"
	"crypto/sha256"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Third-party library imports (external)
import (
	"github.com/gorilla/mux"
	"github.com/lib/pq"
	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"
	"golang.org/x/crypto/bcrypt"
	"golang.org/x/sync/errgroup"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// Local/project imports (should be considered local)
import (
	"myproject/internal/database"
	"myproject/internal/models"
	"myproject/pkg/auth"
	"myproject/pkg/config"
	"myproject/pkg/logger"
	"myproject/pkg/utils"
)

// Relative imports with aliasing
import (
	appconfig "myproject/internal/config"
	applogger "myproject/internal/logger"
	usermodel "myproject/internal/models/user"
)

// Long import lists from single package (candidates for summarization)
import (
	"myproject/internal/handlers/create"
	"myproject/internal/handlers/delete"
	"myproject/internal/handlers/get"
	"myproject/internal/handlers/list"
	"myproject/internal/handlers/update"
)

import (
	"myproject/internal/services/auth"
	"myproject/internal/services/email"
	"myproject/internal/services/logging"
	"myproject/internal/services/notification"
	"myproject/internal/services/payment"
	"myproject/internal/services/storage"
	"myproject/internal/services/user"
	"myproject/internal/services/validation"
)

import (
	"myproject/internal/validators/email"
	"myproject/internal/validators/password"
	"myproject/internal/validators/phone"
	"myproject/internal/validators/postalcode"
	"myproject/internal/validators/creditcard"
	"myproject/internal/validators/sanitizer"
	"myproject/internal/validators/formatter"
	"myproject/internal/validators/slug"
	"myproject/internal/validators/hash"
)

// Blank imports (side effects)
import (
	_ "github.com/lib/pq"
	_ "myproject/internal/migrations"
)

// Dot imports
import (
	. "fmt"
	. "myproject/internal/testutils"
)

// ImportTestService demonstrates various import patterns
type ImportTestService struct {
	db     *gorm.DB
	logger *logrus.Logger
	router *mux.Router
	config *config.Config
}

// NewImportTestService creates a new service instance
func NewImportTestService(db *gorm.DB, logger *logrus.Logger, cfg *config.Config) *ImportTestService {
	return &ImportTestService{
		db:     db,
		logger: logger,
		router: mux.NewRouter(),
		config: cfg,
	}
}

// ProcessData demonstrates usage of external libraries
func (s *ImportTestService) ProcessData(data []interface{}) (interface{}, error) {
	// Using third-party libraries
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Using standard library
	buf := new(bytes.Buffer)
	enc := json.NewEncoder(buf)

	for _, item := range data {
		if err := enc.Encode(item); err != nil {
			return nil, errors.Wrap(err, "encoding failed")
		}
	}

	// Using local utilities
	validated := make([]interface{}, 0)
	for _, item := range data {
		// Would call validation functions here
		validated = append(validated, item)
	}

	// Using gorm
	var result []models.User
	if err := s.db.WithContext(ctx).Find(&result).Error; err != nil {
		return nil, err
	}

	return validated, nil
}

// MakeHTTPRequest demonstrates HTTP client usage
func (s *ImportTestService) MakeHTTPRequest(url string) ([]byte, error) {
	// Using net/http
	client := &http.Client{
		Timeout: 5 * time.Second,
	}

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, errors.Wrap(err, "failed to create request")
	}

	req.Header.Set("User-Agent", "ImportTestService/1.0")

	resp, err := client.Do(req)
	if err != nil {
		s.logger.WithError(err).Error("HTTP request failed")
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	return io.ReadAll(resp.Body)
}

// HashPassword demonstrates crypto usage
func (s *ImportTestService) HashPassword(password string) (string, error) {
	// Using bcrypt
	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return "", errors.Wrap(err, "failed to hash password")
	}

	return string(hash), nil
}

// ProcessConcurrently demonstrates concurrency patterns
func (s *ImportTestService) ProcessConcurrently(items []string) error {
	// Using errgroup
	g, ctx := errgroup.WithContext(context.Background())

	// Using sync primitives
	var mu sync.Mutex
	results := make([]string, 0)

	for _, item := range items {
		item := item // capture loop variable
		g.Go(func() error {
			// Process item
			processed := strings.ToUpper(item)

			mu.Lock()
			results = append(results, processed)
			mu.Unlock()

			return nil
		})
	}

	if err := g.Wait(); err != nil {
		return errors.Wrap(err, "concurrent processing failed")
	}

	return nil
}

// QueryDatabase demonstrates database operations
func (s *ImportTestService) QueryDatabase(userID int) (*models.User, error) {
	var user models.User

	// Using gorm
	if err := s.db.First(&user, userID).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, errors.Wrap(err, "query failed")
	}

	return &user, nil
}

// SetupRoutes demonstrates routing setup
func (s *ImportTestService) SetupRoutes() {
	// Using gorilla/mux
	s.router.HandleFunc("/users", s.handleListUsers).Methods("GET")
	s.router.HandleFunc("/users/{id}", s.handleGetUser).Methods("GET")
	s.router.HandleFunc("/users", s.handleCreateUser).Methods("POST")
	s.router.HandleFunc("/users/{id}", s.handleUpdateUser).Methods("PUT")
	s.router.HandleFunc("/users/{id}", s.handleDeleteUser).Methods("DELETE")
}

func (s *ImportTestService) handleListUsers(w http.ResponseWriter, r *http.Request)   {}
func (s *ImportTestService) handleGetUser(w http.ResponseWriter, r *http.Request)     {}
func (s *ImportTestService) handleCreateUser(w http.ResponseWriter, r *http.Request)  {}
func (s *ImportTestService) handleUpdateUser(w http.ResponseWriter, r *http.Request)  {}
func (s *ImportTestService) handleDeleteUser(w http.ResponseWriter, r *http.Request)  {}

func main() {
	cfg := &config.Config{}
	logger := logrus.New()
	db, _ := gorm.Open(postgres.Open(""), &gorm.Config{})

	service := NewImportTestService(db, logger, cfg)
	service.SetupRoutes()
}
