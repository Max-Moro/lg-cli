/**
 * Comprehensive JavaScript sample for Budget System tests.
 * Contains:
 * - External imports
 * - Local imports
 * - Long comments and JSDoc
 * - Big literals (arrays/objects/template strings)
 * - Public vs private API elements
 */

// … 11 imports omitted (7 lines)

/**
 * Module level long documentation that might be truncated under tight budgets.
 * The text includes several sentences to ensure the comment optimizer has
 * something to work with when switching to keep_first_sentence mode.
 */
export const MODULE_TITLE = 'Budget System Complex Sample';

// … 2 variables omitted (10 lines)

export class PublicService {
    // … field omitted

    /**
     * Public API: gets a user by ID.
     * This doc has multiple sentences to allow truncation under budget.
     */
    getUser(id) {
        return this.#cache.get(String(id)) ?? null;
    }

    // … method omitted (4 lines)

    /** Long method body to allow function body stripping */
    process(list) {
        const out = [];
        for (const u of list) {
            const n = this.#normalize(u);
            out.push(n);
        }
        return { success: true, data: out };
    }
}

// … class omitted (4 lines)

export function publicFunction(name) {
    // … comment omitted
    return toTitle ? toTitle(name) : name;
}

// … function omitted (4 lines)

export default function main() {
    const svc = new PublicService();
    console.log(svc.getUser(1));
}
