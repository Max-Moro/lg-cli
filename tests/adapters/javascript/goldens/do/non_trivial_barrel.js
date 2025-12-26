/**
 * UI Components library.
 */

export { Button } from './Button';
export { Input } from './Input';

/**
 * Create a pre-configured component instance.
 */
export function createComponent(type, props) {
    const Component = type === 'button' ? Button : Input;
    return new Component(props);
}
