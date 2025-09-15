/**
 * Non-barrel file sample for testing barrel file detection.
 * This file should NOT be recognized as a barrel file.
 */

import { User, UserRole } from './models/user';
import { Logger } from './utils/logger';

interface ServiceConfig {
    endpoint: string;
    timeout: number;
    retries: number;
}

export class UserService {
    private logger: Logger;
    private config: ServiceConfig;
    
    constructor(config: ServiceConfig) {
        this.config = config;
        this.logger = new Logger('UserService');
    }
    
    public async createUser(userData: Partial<User>): Promise<User> {
        this.logger.info('Creating new user', userData);
        
        const validation = this.validateUserData(userData);
        if (!validation.isValid) {
            throw new Error(`Invalid user data: ${validation.errors.join(', ')}`);
        }
        
        try {
            const response = await fetch(`${this.config.endpoint}/users`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(userData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const user = await response.json();
            this.logger.info('User created successfully', { id: user.id });
            
            return user;
        } catch (error) {
            this.logger.error('Failed to create user', error);
            throw error;
        }
    }
    
    public async getUserById(id: number): Promise<User | null> {
        if (id <= 0) {
            throw new Error('User ID must be positive');
        }
        
        try {
            const response = await fetch(`${this.config.endpoint}/users/${id}`);
            
            if (response.status === 404) {
                return null;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            this.logger.error('Failed to fetch user', { id, error });
            throw error;
        }
    }
    
    private validateUserData(userData: Partial<User>): { isValid: boolean; errors: string[] } {
        const errors: string[] = [];
        
        if (!userData.name || userData.name.trim().length === 0) {
            errors.push('Name is required');
        }
        
        if (!userData.email || !this.isValidEmail(userData.email)) {
            errors.push('Valid email is required');
        }
        
        if (userData.role && !Object.values(UserRole).includes(userData.role)) {
            errors.push('Invalid user role');
        }
        
        return {
            isValid: errors.length === 0,
            errors
        };
    }
    
    private isValidEmail(email: string): boolean {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
}

export const DEFAULT_SERVICE_CONFIG: ServiceConfig = {
    endpoint: 'http://localhost:3000/api',
    timeout: 5000,
    retries: 3
};

export function createUserService(config?: Partial<ServiceConfig>): UserService {
    const finalConfig = { ...DEFAULT_SERVICE_CONFIG, ...config };
    return new UserService(finalConfig);
}