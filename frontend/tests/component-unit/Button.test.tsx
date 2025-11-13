// tests/component-unit/Button.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
// If your Button is a default export, adjust import accordingly
import { Button } from '@/components/ui/Button'
import { forwardRef } from 'react'

// Helper to get the button by its accessible name
const byName = (name: string | RegExp) =>
    screen.getByRole('button', { name })

describe('Button', () => {
    it('renders its children (accessible name)', () => {
        render(<Button>Click Me</Button>)
        expect(byName(/click me/i)).toBeInTheDocument()
    })

    it('calls onClick on mouse click', async () => {
        const user = userEvent.setup()
        const handleClick = vi.fn()
        render(<Button onClick={handleClick}>Submit</Button>)
        await user.click(byName(/submit/i))
        expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('is not clickable when disabled (mouse + keyboard)', async () => {
        const user = userEvent.setup()
        const handleClick = vi.fn()
        render(
            <Button disabled onClick={handleClick}>
                Disabled
            </Button>
        )

        const el = byName(/disabled/i)
        expect(el).toBeDisabled()

        await user.click(el)
        await user.keyboard('{Enter}')
        await user.keyboard(' ')
        expect(handleClick).not.toHaveBeenCalled()
    })

    it('is focusable when not disabled and supports keyboard activation', async () => {
        const user = userEvent.setup()
        const handleClick = vi.fn()
        render(<Button onClick={handleClick}>Focusable</Button>)

        const el = byName(/focusable/i)
        el.focus()
        expect(el).toHaveFocus()

        await user.keyboard('{Enter}')
        await user.keyboard(' ')
        // Enter + Space usually both activate <button>
        expect(handleClick).toHaveBeenCalledTimes(2)
    })

    it('respects type="submit" inside a form', async () => {
        const user = userEvent.setup()
        const onSubmit = vi.fn((e: React.FormEvent) => e.preventDefault())

        render(
            <form onSubmit={onSubmit}>
                <Button type="submit">Save</Button>
            </form>
        )

        await user.click(byName(/save/i))
        expect(onSubmit).toHaveBeenCalledTimes(1)
    })

    it('forwards extra props (e.g., data-* and className)', () => {
        render(
            <Button data-testid="btn" className="test-token">
                Extra
            </Button>
        )
        const el = screen.getByTestId('btn')
        // Prefer testing a stable token you own (data attr) or a known class token
        expect(el).toHaveClass('test-token')
    })

    // If your Button supports variants via cva (shadcn pattern), test a stable class token.
    // Adjust 'variant' name and class token to your implementation.
    it('applies variant classes', () => {
        render(<Button variant="outline">Outline</Button>)
        const el = byName(/outline/i)
        // Replace with a stable class or data attribute you control
        expect(el.className).toMatch(/outline/i)
    })

    // If your Button supports `asChild` (e.g., to render <a>), test polymorphism.
    // This sample uses a naive child that forwards props to <a>.
    it('can render as child (polymorphic) and replaces the button', async () => {
        const user = userEvent.setup()
        const Link = forwardRef<
            HTMLAnchorElement,
            React.ComponentPropsWithoutRef<'a'>
        >((props, ref) => <a ref={ref} {...props} />)

        const onClick = vi.fn((e: React.MouseEvent) => e.preventDefault())

        render(
            <Button asChild onClick={onClick}>
                <Link href="/profile">Profile</Link>
            </Button>
        )

        // 1. ASSERT that the link (<a> tag) is on the screen
        const linkElement = screen.getByRole('link', { name: /profile/i })
        expect(linkElement).toBeInTheDocument()

        // 2. THIS IS THE REAL TEST: Assert that the <button> is NOT on the screen
        const buttonElement = screen.queryByRole('button')
        expect(buttonElement).not.toBeInTheDocument()

        // 3. Assert the click still worked
        await user.click(linkElement)
        expect(onClick).toHaveBeenCalledTimes(1)
    })
})
