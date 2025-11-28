/**
 * JavaScript module for testing public API filtering.
 */

import { EventEmitter } from 'events';

// Public module-level constants (should be preserved)
export const PUBLIC_VERSION = '1.0.0';
export const API_ENDPOINT = 'https://api.example.com';

// Private module-level constants (should be filtered out)
const PRIVATE_SECRET = 'internal-use-only';
const INTERNAL_CONFIG = { debug: true, verbose: false };

// Public class with mixed visibility members
export class UserManager {
    // Public properties
    version = PUBLIC_VERSION;
    isInitialized = false;

    // Private properties (should be filtered out with public_api_only)
    #internalCache = new Map();
    #metrics = { processTime: 0, memoryUsage: 0 };

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
    #validateUserData(userData) {
        if (!userData.name || !userData.email) {
            throw new Error('Name and email are required');
        }

        if (!this.#isValidEmail(userData.email)) {
            throw new Error('Invalid email format');
        }
    }

    #generateId() {
        return Math.floor(Math.random() * 1000000);
    }

    #isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    async #fetchUserFromApi(id) {
        try {
            const response = await fetch(`${this.apiEndpoint}/users/${id}`);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            this.#logError('Failed to fetch user', error);
        }

        return null;
    }

    #initialize() {
        this.config = { ...INTERNAL_CONFIG };
        this.isInitialized = true;
    }

    #logError(message, error) {
        console.error(`[UserManager] ${message}:`, error);
    }

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
    static #formatInternalId(id) {
        return `internal_${id.toString().padStart(6, '0')}`;
    }

    // Public readonly property with getter
    get userCount() {
        return this.#internalCache.size;
    }

    // Private readonly property with getter (should be filtered out)
    get #internalState() {
        return {
            cacheSize: this.#internalCache.size,
            metrics: this.#metrics
        };
    }
}

// Private class (not exported, should be filtered out)
class InternalLogger {
    #logs = [];

    log(message) {
        this.#logs.push(`${new Date().toISOString()}: ${message}`);
    }

    getLogs() {
        return [...this.#logs];
    }

    #clearLogs() {
        this.#logs = [];
    }
}

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
    _validateConfig(config) {
        throw new Error('Method must be implemented');
    }
}

// Public enum-like object (should be preserved)
export const UserStatus = {
    ACTIVE: 'active',
    INACTIVE: 'inactive',
    PENDING: 'pending',
    BANNED: 'banned'
};

// Private enum-like object (not exported, should be filtered out)
const InternalEventType = {
    USER_CREATED: 'user_created',
    USER_UPDATED: 'user_updated',
    CACHE_CLEARED: 'cache_cleared'
};

// Public functions (should be preserved)
export function createUserManager(endpoint) {
    return new UserManager(endpoint);
}

export function isValidUserRole(role) {
    return UserManager.validateUserRole(role);
}

// Private functions (not exported, should be filtered out)
function logInternalEvent(event, data) {
    console.log(`[Internal] ${event}:`, data);
}

function processInternalMetrics(metrics) {
    // Process internal metrics
    console.log('Processing metrics:', metrics);
}

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
    _internalFormatting(text) {
        return text.toLowerCase().replace(/\s+/g, '_');
    }
};

// Private namespace-like object (not exported, should be filtered out)
const InternalUtils = {
    debugLog(message) {
        if (INTERNAL_CONFIG.debug) {
            console.log(`[Debug] ${message}`);
        }
    },

    measurePerformance(fn) {
        const start = performance.now();
        const result = fn();
        const end = performance.now();
        console.log(`Performance: ${end - start}ms`);
        return result;
    }
};

// Default export (should be preserved)
export default UserManager;
