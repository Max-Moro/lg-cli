/**
 * Barrel file sample for testing barrel file detection.
 * This file should be recognized as a barrel file and potentially skipped.
 */

// Re-exports from various modules
export { User, UserRole, UserStatus } from './models/user';
export { Post, Comment, Tag } from './models/content';
export { DatabaseConnection, QueryBuilder } from './database';
export { Logger, LogLevel } from './utils/logger';
export { ConfigManager, Environment } from './config';

// Re-export with renaming
export { ValidationError as InputValidationError } from './errors/validation';
export { NetworkError as HttpError } from './errors/network';

// Re-export everything from utils
export * from './utils/helpers';
export * from './utils/formatters';
export * from './utils/validators';

// Re-export types only
export type { ApiResponse, ApiError } from './api/types';
export type { DatabaseConfig, ConnectionOptions } from './database/types';

// Default re-export
export { default as ApiClient } from './api/client';
export { default as EventEmitter } from './events/emitter';

// Mixed re-exports and simple declarations
export const API_VERSION = '1.0.0';
export const DEFAULT_TIMEOUT = 5000;

// Simple utility function (still barrel-like if most content is re-exports)
export function createDefaultConfig() {
    return {
        timeout: DEFAULT_TIMEOUT,
        version: API_VERSION
    };
}