// … comment omitted
/**
 * Comprehensive TypeScript sample for Budget System tests.
 */

// … comment omitted
// … 3 imports omitted

// … comment omitted
// … 2 imports omitted

/**
 * Module level long documentation that might be truncated under tight budgets.
 */
export const MODULE_TITLE = 'Budget System Complex Sample';

const LONG_TEXT = `This is an extremely long template literal that is designed to be trimmed 
by the literal optimizer when budgets are small. It repeats a message…`; // literal string (−7 tokens)

const BIG_OBJECT = {
  users: Array.from({ length: 50 }, (_, i) => ({ id: i + 1, name: `User ${i + 1}`, active: i % 2 === 0 })),
  // … (1 more, −53 tokens)
};

export class PublicService {
  // … field omitted

  /**
   * Public API: gets a user by ID.
   */
  public getUser(id: number): User | null // … method body omitted (3 lines)

  // … comment omitted
  // … method omitted

  /** Long method body to allow function body stripping. */
  public process(list: User[]): ApiResponse<User[]> // … method body omitted (8 lines)
}

// … class omitted

export function publicFunction(name: string): string // … function body omitted (4 lines)

// … function omitted

export default function main(): void // … function body omitted (4 lines)
