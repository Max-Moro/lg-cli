/**
 * Comprehensive JavaScript sample for Budget System tests.
 */

// … comment omitted
// … 8 imports omitted (3 lines)

// … comment omitted
// … 3 imports omitted (2 lines)

/**
 * Module level long documentation that might be truncated under tight budgets.
 */
export const MODULE_TITLE = 'Budget System Complex Sample';

// … 2 variables omitted (10 lines)

export class PublicService {
    // … field omitted

    /**
     * Public API: gets a user by ID.
     */
    getUser(id) {
        return this.#cache.get(String(id)) ?? null;
    }

    // … comment omitted
    // … method omitted (3 lines)

    /** Long method body to allow function body stripping. */
    process(list) {
        // … method body omitted (6 lines)
    }
}

// … class omitted (4 lines)

export function publicFunction(name) {
    // … function body omitted (2 lines)
}

// … function omitted (4 lines)

export default function main() {
    // … function body omitted (2 lines)
}
