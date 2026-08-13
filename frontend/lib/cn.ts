/**
 * Tiny class-name joiner.
 *
 * Deliberately not clsx/tailwind-merge: the components here compose classes by
 * appending, never by overriding a conflicting utility, so a dependency that
 * resolves Tailwind conflicts would be dead weight in the bundle.
 */
export type ClassValue = string | false | null | undefined;

export function cn(...classes: ClassValue[]): string {
  return classes.filter(Boolean).join(' ');
}

export default cn;
