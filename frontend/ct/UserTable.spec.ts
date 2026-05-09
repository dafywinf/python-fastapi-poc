import { expect, test } from '@playwright/experimental-ct-vue'
import type { User } from '../src/api/users'
import UserTable from '../src/features/users/components/UserTable.vue'

const mockUsers: User[] = [
  {
    id: 1,
    email: 'alice@example.com',
    name: 'Alice',
    picture: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    email: 'bob@example.com',
    name: 'Bob',
    picture: 'https://img.example.com/bob.jpg',
    created_at: '2026-01-02T00:00:00Z',
  },
]

test.describe('UserTable', () => {
  test('renders user rows with name and email', async ({ mount }) => {
    const component = await mount(UserTable, {
      props: { users: mockUsers, loading: false, error: null },
    })

    await expect(component.getByTestId('users-table')).toBeVisible()
    // exact: true prevents "Alice" from substring-matching "alice@example.com"
    await expect(component.getByText('Alice', { exact: true })).toBeVisible()
    await expect(component.getByText('alice@example.com', { exact: true })).toBeVisible()
    await expect(component.getByText('Bob', { exact: true })).toBeVisible()
    await expect(component.getByText('bob@example.com', { exact: true })).toBeVisible()
  })

  test('shows empty state when no users are provided', async ({ mount }) => {
    const component = await mount(UserTable, {
      props: { users: [], loading: false, error: null },
    })

    await expect(component.getByTestId('users-empty')).toBeVisible()
    await expect(component.getByText('No users have logged in yet.')).toBeVisible()
  })

  test('shows error banner when error prop is set', async ({ mount }) => {
    const component = await mount(UserTable, {
      props: { users: [], loading: false, error: 'Network error' },
    })

    await expect(component.getByTestId('users-error')).toBeVisible()
    await expect(component.getByText('Network error')).toBeVisible()
  })

  test('shows initials avatar when user has no picture', async ({ mount }) => {
    const component = await mount(UserTable, {
      props: { users: [mockUsers[0]!], loading: false, error: null },
    })

    // Alice has no picture — the initials span should render exactly "A"
    // exact: true prevents substring-matching "Active", "Alice", etc.
    await expect(component.getByText('A', { exact: true })).toBeVisible()
    await expect(component.getByRole('img')).not.toBeVisible()
  })

  test('shows image avatar when user has a picture URL', async ({ mount }) => {
    const component = await mount(UserTable, {
      props: { users: [mockUsers[1]!], loading: false, error: null },
    })

    const avatar = component.getByRole('img', { name: 'Bob' })
    await expect(avatar).toBeVisible()
    await expect(avatar).toHaveAttribute('src', 'https://img.example.com/bob.jpg')
  })

  test('renders a copy email button for each user row', async ({ mount }) => {
    const component = await mount(UserTable, {
      props: { users: mockUsers, loading: false, error: null },
    })

    await expect(component.getByTestId('copy-email-1')).toBeVisible()
    await expect(component.getByTestId('copy-email-2')).toBeVisible()
  })

  test('shows an Active status tag for each user', async ({ mount }) => {
    const component = await mount(UserTable, {
      props: { users: mockUsers, loading: false, error: null },
    })

    await expect(component.getByText('Active')).toHaveCount(2)
  })

  test('table container is rendered', async ({ mount }) => {
    const component = await mount(UserTable, {
      props: { users: mockUsers, loading: false, error: null },
    })

    await expect(component.getByTestId('users-table-container')).toBeVisible()
  })
})
