/**
 * Complex TypeScript test module combining multiple optimization types.
 * 
 * This module is designed to test multiple optimizations without
 * them interfering with each other. Each optimization should have
 * clear, non-overlapping effects.
 */

// Mixed imports for import optimization
import React from 'react';
import { Component, useState, useEffect } from 'react';
import * as lodash from 'lodash';  // External library
import { UserService } from './services/user-service';  // Local import

// Long import list for summarization testing
import {
    Injectable, Module, Controller, Get, Post, Put, Delete,
    Body, Param, Query, HttpStatus, UseGuards, ValidationPipe
} from '@nestjs/common';

export interface DataModel {
    name: string;
    value: number;
    metadata?: Record<string, any>;
}

/**
 * Main demo class for multiple optimization types.
 * 
 * This class is designed so different optimizations
 * can work on separate parts without interference.
 */
export class ComplexOptimizationDemo {
    // Class-level literals (literal optimization target)
    private static readonly DEFAULT_CONFIG = {
        timeout: 30000,
        retries: 3,
        endpoints: [
            '/api/v1/users', '/api/v1/posts', '/api/v1/comments',
            '/api/v1/categories', '/api/v1/tags', '/api/v1/settings'
        ],
        features: {
            caching: true,
            logging: true,
            monitoring: false,
            analytics: true,
            compression: false
        }
    };
    
    private static readonly LARGE_DATA_SET = [
        'item_001', 'item_002', 'item_003', 'item_004', 'item_005',
        'item_006', 'item_007', 'item_008', 'item_009', 'item_010',
        'item_011', 'item_012', 'item_013', 'item_014', 'item_015',
        'item_016', 'item_017', 'item_018', 'item_019', 'item_020',
        'item_021', 'item_022', 'item_023', 'item_024', 'item_025'
    ];
    
    public name: string;
    public config: Record<string, any>;
    public data: any[];
    public initialized: boolean;
    
    constructor(name: string, config?: Record<string, any>) {
        /**
         * Trivial constructor for field optimization.
         * 
         * This constructor only does simple field assignments
         * and should be targeted by field optimization.
         */
        // Simple field assignments (field optimization target)
        this.name = name;
        this.config = config || {};
        this.data = [];
        this.initialized = true;
    }
    
    /**
     * Public method with substantial body for function body optimization.
     * 
     * This method has enough logic to be worth stripping the body
     * while preserving the signature and docstring.
     */
    public processDataWithAnalytics(inputData: DataModel[]): Record<string, number> {
        // Comment that should be handled by comment optimization
        const result: Record<string, number> = {};
        
        // Processing loop with business logic
        for (const item of inputData) {
            const key = item.name.toLowerCase();
            if (!(key in result)) {
                result[key] = 0;
            }
            result[key] += item.value;
        }
        
        // TODO: Consider using Map instead of object
        // Additional analytics processing
        const total = Object.values(result).reduce((sum, val) => sum + val, 0);
        result['_total'] = total;
        result['_average'] = total / inputData.length;
        
        return result;
    }
    
    /**
     * Private method that should be filtered by public API optimization.
     * 
     * This method should be removed entirely when public_api_only is enabled,
     * so function body optimization won't have a chance to process it.
     */
    private processInternalData(): string {
        // Private implementation details
        const temp = this.name.toUpperCase();
        const processed = temp.replace(/\s+/g, '_');
        const timestamped = `${processed}_${Date.now()}`;
        return timestamped;
    }
    
    // Trivial property getters/setters for field optimization
    get simpleName(): string {
        return this.name;
    }
    
    set simpleName(value: string) {
        this.name = value;
    }
    
    get simpleConfig(): Record<string, any> {
        return this.config;
    }
    
    set simpleConfig(value: Record<string, any>) {
        this.config = value;
    }
    
    /**
     * Method combining comment and literal optimization targets.
     * 
     * This method has various comment types and literal data
     * that should be processed by different optimizers.
     */
    public processWithCommentsAndLiterals(): Record<string, any> {
        // Regular comment for comment optimization
        const processingConfig = {
            options: {
                method: 'advanced',
                validation: true,
                errorHandling: 'strict',
                loggingLevel: 'DEBUG',
                outputFormat: 'json',
                compression: true,
                caching: true
            },
            dataSources: [
                'primaryDatabase', 'secondaryDatabase', 'cacheLayer',
                'externalAPI', 'fileSystem', 'memoryStore', 'eventStream'
            ],
            timeouts: {
                database: 5000,
                api: 3000,
                cache: 1000,
                fileSystem: 2000
            }
        };  // Large literal for literal optimization
        
        // FIXME: This needs better error handling
        // TODO: Add comprehensive validation for all config options
        
        const longDescription = `This is a comprehensive description that contains detailed information about the data processing operation. It includes multiple sentences with extensive details about the algorithm implementation, performance characteristics, error handling strategies, and various edge cases that need to be considered during execution.`;  // String literal for trimming
        
        return {
            config: processingConfig,
            description: longDescription,
            timestamp: new Date().toISOString()
        };
    }
}

/**
 * Public utility function for function body optimization.
 * 
 * This function should keep its signature and docstring
 * but have its body optimized by function body optimization.
 * Won't be filtered by public API since it's exported.
 */
export function processDataModels(items: DataModel[]): { valid: DataModel[], invalid: DataModel[] } {
    // Comment that can be optimized
    const categorized = { valid: [], invalid: [] };
    
    // Complex processing logic
    for (const item of items) {
        if (item.value > 0 && item.name && item.name.trim().length > 0) {
            categorized.valid.push(item);
        } else {
            categorized.invalid.push(item);
        }
    }
    
    // Additional validation and processing
    categorized.valid.forEach(item => {
        if (!item.metadata) {
            item.metadata = { processed: true, timestamp: Date.now() };
        }
    });
    
    // TODO: Add more sophisticated validation rules
    return categorized;
}

/**
 * Private utility function for public API filtering.
 * 
 * This entire function should be removed by public API optimization
 * since it's not exported.
 */
function internalUtilityFunction(): string[] {
    // This won't be processed by other optimizations
    // because the whole function will be removed
    const internalData = [
        'private_item_1', 'private_item_2', 'private_item_3',
        'internal_config', 'debug_info', 'system_metadata'
    ];
    
    const processed = internalData.map(item => 
        item.toUpperCase().replace(/_/g, '-')
    );
    
    return processed;
}

// Short helper function (won't trigger function body optimization due to size)
export function createSimpleModel(name: string, value: number): DataModel {
    return { name, value };  // Should be preserved due to size
}

// Exported class with mixed visibility for public API testing
export class PublicDataProcessor {
    public version: string = '1.0.0';
    private internalCache: Map<string, any> = new Map();
    
    constructor(initialData?: any[]) {
        // Trivial constructor
        if (initialData) {
            this.loadData(initialData);
        }
    }
    
    // Public method (preserved by public API optimization)
    public processPublicData(data: any[]): any[] {
        const results = [];
        for (const item of data) {
            if (this.validateItem(item)) {
                results.push(this.transformItem(item));
            }
        }
        return results;
    }
    
    // Private method (removed by public API optimization)
    private validateItem(item: any): boolean {
        return item && typeof item === 'object' && 'id' in item;
    }
    
    // Private method (removed by public API optimization)
    private transformItem(item: any): any {
        return { ...item, processed: true };
    }
    
    // Private method (removed by public API optimization)
    private loadData(data: any[]): void {
        data.forEach((item, index) => {
            this.internalCache.set(`item_${index}`, item);
        });
    }
}

// Private class (not exported, removed by public API optimization)
class InternalHelper {
    private static instance: InternalHelper;
    
    public static getInstance(): InternalHelper {
        if (!InternalHelper.instance) {
            InternalHelper.instance = new InternalHelper();
        }
        return InternalHelper.instance;
    }
    
    public processInternalLogic(data: any): any {
        // This entire class will be removed by public API optimization
        return { processed: data, timestamp: Date.now() };
    }
}

// Arrow function that's short (preserved by function body optimization)
export const quickHelper = (x: number) => x * 2;

// Module execution block (should be preserved)
if (require.main === module) {
    // Main execution code (preserved by public API optimization)
    const demo = new ComplexOptimizationDemo('test', { debug: true });
    const models = [
        createSimpleModel('item1', 100),
        createSimpleModel('item2', -50)
    ];
    
    const result = processDataModels(models);
    console.log('Processing result:', result);
    
    // Some comments for comment optimization in main block
    // TODO: Add comprehensive integration testing
    const processed = demo.processDataWithAnalytics(models);
    console.log('Analytics result:', processed);
}
