/**
 * JavaScript module for testing import optimization.
 */

// External library imports (should be considered external)
import React from 'react';
import { Component, useState, useEffect, useCallback, useMemo } from 'react';
// … 6 imports omitted
import * as lodash from 'lodash';
import axios from 'axios';
import moment from 'moment';
import { v4 as uuidv4 } from 'uuid';

// Scoped package imports (external)
import { Router, Request, Response } from '@types/express';
import express from 'express';

// Node.js built-in modules (external/standard library)
import * as fs from 'fs';
import * as path from 'path';
import { promisify } from 'util';
import { EventEmitter } from 'events';
import { Readable, Writable, Transform } from 'stream';

// Local/relative imports (should be considered local)
import { UserService } from './services/user-service.js';
import { DatabaseConnection } from './database/connection.js';
import { ValidationError, NetworkError } from './errors.js';
import { formatDate, parseJson } from './utils/helpers.js';
import { ApiResponse, UserModel, PostModel } from './types.js';

// Relative imports with different depth levels
import { SharedUtility } from '../shared/utilities.js';
import { CoreModule } from '../../core/core.module.js';
import { AppConfig } from '../../../config/app.config.js';

// Import with aliasing
import { Logger as AppLogger } from './utils/logger.js';
import { Config as AppConfig2 } from './config/app.config.js';
import { default as HttpClient } from './http/client.js';

// Mixed import styles on single line
import fs2, { readFile, writeFile } from 'fs';
import path2, { join, resolve, dirname } from 'path';

// Long import lists (candidates for summarization)
// … 23 imports omitted

// Dynamic imports (should be preserved as-is)
const dynamicModule = async () => {
    const { default: chalk } = await import('chalk');
    return chalk;
};

// Conditional imports
let csvParser;
try {
    csvParser = require('csv-parser');
} catch (error) {
    console.warn('csv-parser not available');
}

export class ImportTestService {
    constructor(userService, dbConnection, logger) {
        this.userService = userService;
        this.dbConnection = dbConnection;
        this.logger = logger;
    }

    async processData(data) {
        // Using external libraries
        const processed = lodash.map(data, item => ({
            id: uuidv4(),
            timestamp: moment().toISOString(),
            ...item
        }));

        // Using local utilities
        const validated = processed.map(item =>
            validateEmail(item.email) ? item : null
        ).filter(Boolean);

        // Using Node.js built-ins
        const filePath = path.join(__dirname, 'output.json');
        await promisify(fs.writeFile)(filePath, JSON.stringify(validated));

        return {
            success: true,
            data: validated,
            timestamp: formatDate(new Date())
        };
    }

    async makeHttpRequest(url) {
        try {
            // Using axios
            const response = await axios.get(url, {
                timeout: 5000,
                headers: {
                    'User-Agent': 'ImportTestService/1.0'
                }
            });

            return response.data;
        } catch (error) {
            this.logger.error('HTTP request failed', error);
            throw new NetworkError('Request failed');
        }
    }
}

// Re-exports (should be handled appropriately)
export { UserService } from './services/user-service.js';
export { DatabaseConnection } from './database/connection.js';
export * from './types.js';

// Default export
export default ImportTestService;
