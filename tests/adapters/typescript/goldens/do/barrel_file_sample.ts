// Barrel file example
export { ComponentA } from './components/ComponentA';
export { ComponentB } from './components/ComponentB';
export { ServiceA, ServiceB } from './services';
export * from './utils';
export { default as MainComponent } from './MainComponent';

// Re-export external libraries
export { Observable } from 'rxjs';
export type { User, UserResponse } from './types';
