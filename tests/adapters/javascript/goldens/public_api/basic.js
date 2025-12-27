/**
 * JavaScript module for testing public API filtering.
 */

import { EventEmitter } from 'events';

// Public module-level constants (should be preserved)
export const PUBLIC_VERSION = '1.0.0';
export const API_ENDPOINT = 'https://api.example.com';

// … 2 variables omitted (3 lines)

// Public class with mixed visibility members
export class UserManager {
    // Public properties
    version = PUBLIC_VERSION;
    isInitialized = false;

    // … 2 fields omitted (3 lines)

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

    // … 6 methods omitted (34 lines)

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

    // … method omitted (4 lines)

    // Public readonly property with getter
    get userCount() {
        return this.#internalCache.size;
    }

    // … method omitted (7 lines)
}

// … class omitted (13 lines)

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

    // … method omitted (4 lines)
}

// Public enum-like object (should be preserved)
export const UserStatus = {
    ACTIVE: 'active',
    INACTIVE: 'inactive',
    PENDING: 'pending',
    BANNED: 'banned'
};

// … variable omitted (6 lines)

// Public functions (should be preserved)
export function createUserManager(endpoint) {
    return new UserManager(endpoint);
}

export function isValidUserRole(role) {
    return UserManager.validateUserRole(role);
}

// … 2 functions omitted (8 lines)

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

    // … method omitted (4 lines)
};

// … variable omitted (15 lines)

// Default export (should be preserved)
export default UserManager;
