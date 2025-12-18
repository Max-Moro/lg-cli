
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
  private cache = new Map<string, User>();

  /**
   * Public API: gets a user by ID.
   * This doc has multiple sentences to allow truncation under budget.
   */
  public getUser(id: number): User | null {
    return this.cache.get(String(id)) ?? null;
  }

  
  private _normalize(u: Partial<User>): User {
    return { id: u.id!, name: (u.name ?? '').trim(), email: u.email ?? '' } as User;
  }

  /** Long method body to allow function body stripping */
  public process(list: User[]): ApiResponse<User[]> {
    const out: User[] = [];
    for (const u of list) {
      const n = this._normalize(u);
      out.push(n);
    }
    return { success: true, data: out } as ApiResponse<User[]>;
  }
}

class _InternalOnly {
  
  public doWork(): void { /* noop */ }
}

export function publicFunction(name: string): string {
  
  return toTitle ? toTitle(name) : name;
}

function privateFunction(data: string[]): string[] {
  
  return data.map(s => s.trim());
}

export default function main(): void {
  const svc = new PublicService();
  console.log(svc.getUser(1));
}
