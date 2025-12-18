
/**
 * Comprehensive TypeScript sample for Budget System tests.
 * Contains:
 * - External imports
 * - Local imports
 * - Long comments and JSDoc
 * - Big literals (arrays/objects/template strings)
 * - Public vs private API elements
 */







/**
 * Module level long documentation that might be truncated under tight budgets.
 * The text includes several sentences to ensure the comment optimizer has
 * something to work with when switching to keep_first_sentence mode.
 */
export const MODULE_TITLE = 'Budget System Complex Sample';

const LONG_TEXT = `This is an extremely long template literal that is designed to be trimmed 
by the literal optimizer when budgets are small. It repeats a message…`;

const BIG_OBJECT = {
  users: Array.from({ length: 50 }, (_, i) => ({ id: i + 1, name: `User ${i + 1}`, active: i % 2 === 0 })),
  // … (1 more, −53 tokens)
};

export class PublicService {
  

  /**
   * Public API: gets a user by ID.
   * This doc has multiple sentences to allow truncation under budget.
   */
  public getUser(id: number): User | null 

  
  

  /** Long method body to allow function body stripping */
  public process(list: User[]): ApiResponse<User[]> 
}



export function publicFunction(name: string): string 



export default function main(): void
