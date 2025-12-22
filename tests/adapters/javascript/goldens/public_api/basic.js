/**
 * JavaScript module for testing public API filtering.
 */

// … import omitted

// Public module-level constants (should be preserved)
export const PUBLIC_VERSION = '1.0.0';
export const API_ENDPOINT = 'https://api.example.com';

// Private module-level constants (should be filtered out)
// … 2 variables omitted

// Public class with mixed visibility members
export class UserManager {
    // Public properties
    version = PUBLIC_VERSION;
    isInitialized = false;

    // Private properties (should be filtered out with public_api_only)
    // … 2 fields omitted

    constructor(apiEndpoint = API_ENDPOINT) {
        this.apiEndpoint = apiEndpoint;
        this.#initialize();
    }

    // Public methods (should be preserved)
    async createUser(userData) {
        this.#validateUserData(userData);

        const user = {
            id: this.#generateId(),
            name: userData.name,
            email: userData.email,
            createdAt: new Date()
        };

        this.#internalCache.set(user.email, user);
        return user;
    }

    async getUserById(id) {
        for (const user of this.#internalCache.values()) {
            if (user.id === id) {
                return user;
            }
        }

        return await this.#fetchUserFromApi(id);
    }

    getAllUsers() {
        return Array.from(this.#internalCache.values());
    }

    // Private methods (should be filtered out)
    // … 6 methods omitted (33 lines)

    // Public static methods (should be preserved)
    static validateUserRole(role) {
        return ['admin', 'user', 'guest'].includes(role);
    }

    static createDefaultUser() {
        return {
            id: 0,
            name: 'Default User',
            email: 'default@example.com',
            createdAt: new Date()
        };
    }

    // Private static methods (should be filtered out)
    // … method omitted (3 lines)

    // Public readonly property with getter
    get userCount() {
        return this.#internalCache.size;
    }

    // Private readonly property with getter (should be filtered out)
    // … method omitted (6 lines)
}

// Private class (not exported, should be filtered out)
// … class omitted (12 lines)

// Public abstract-like class (should be preserved)
export class BaseService {
    constructor() {
        if (new.target === BaseService) {
            throw new Error('Cannot instantiate abstract class');
        }
    }

    async initialize() {
        throw new Error('Method must be implemented');
    }

    getServiceInfo() {
        return {
            name: this.serviceName,
            version: PUBLIC_VERSION
        };
    }

    // Protected-like method (should be filtered out in public API)
    // … method omitted (3 lines)
}

// Public enum-like object (should be preserved)
export const UserStatus = {
    ACTIVE: 'active',
    INACTIVE: 'inactive',
    PENDING: 'pending',
    BANNED: 'banned'
};

// Private enum-like object (not exported, should be filtered out)
// … variable omitted (5 lines)

// Public functions (should be preserved)
export function createUserManager(endpoint) {
    return new UserManager(endpoint);
}

export function isValidUserRole(role) {
    return UserManager.validateUserRole(role);
}

// Private functions (not exported, should be filtered out)
// … 2 functions omitted (7 lines)

// Exported namespace-like object (should be preserved)
export const UserUtils = {
    formatUserName(user) {
        return `${user.name} (${user.email})`;
    },

    getUserAge(user) {
        const now = new Date();
        const created = new Date(user.createdAt);
        return Math.floor((now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24));
    },

    // Private namespace member (should be filtered out)
    // … method omitted (3 lines)
};

// Private namespace-like object (not exported, should be filtered out)
// … variable omitted (14 lines)

// Default export (should be preserved)
export default UserManager;
