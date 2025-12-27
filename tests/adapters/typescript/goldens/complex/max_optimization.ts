// … comment omitted
/**
 * Comprehensive TypeScript sample for Budget System tests.
 */

// … 11 imports omitted (7 lines)

/**
 * Module level long documentation that might be truncated under tight budgets.
 */
export const MODULE_TITLE = 'Budget System Complex Sample';

const LONG_TEXT = `This is an extremely long template literal that is designed to be trimmed 
by the literal optimizer when budgets are small. It repeats a message…`; // literal string (−4 tokens)

const BIG_OBJECT = {
  users: Array.from({ length: 50 }, (_, i) => ({ id: i + 1, name: `User ${i + 1}`, active: i % 2 === 0 })),
  // … (1 more, −53 tokens)
};

export class PublicService {
  // … field omitted

  /**
   * Public API: gets a user by ID.
   */
  public getUser(id: number): User | null {
    return this.cache.get(String(id)) ?? null;
  }

  // … method omitted (4 lines)

  /** Long method body to allow function body stripping. */
  public process(list: User[]): ApiResponse<User[]> {
    // … method body omitted (6 lines)
  }
}

// … class omitted (4 lines)

export function publicFunction(name: string): string {
  // … function body omitted (2 lines)
}

// … function omitted (4 lines)

export default function main(): void {
  // … function body omitted (2 lines)
}
