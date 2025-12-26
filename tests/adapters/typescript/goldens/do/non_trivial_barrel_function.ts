/**
 * UI Components library.
 *
 * Re-exports all public components for convenient imports.
 */

export { Button } from './Button';
export { Input } from './Input';
export { Select } from './Select';
export { Modal } from './Modal';
export { Toast } from './Toast';

export type { ButtonProps } from './Button';
export type { InputProps } from './Input';
export type { SelectProps, SelectOption } from './Select';

/**
 * Create a pre-configured toast notification.
 * Convenience wrapper used across the app.
 */
export function showToast(message: string, type: 'success' | 'error' | 'info' = 'info'): void {
    Toast.show({ message, type, duration: type === 'error' ? 5000 : 3000 });
}
