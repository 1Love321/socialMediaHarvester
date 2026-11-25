import { render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from './App.jsx'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(
    JSON.stringify({ email: 'first.admin@harvester.test', role: 'ADMIN' }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  )))
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('shows the sidebar shell with empty Data, Operate and Admin groups', async () => {
  render(<App />)

  const sidebar = screen.getByRole('navigation', { name: 'Sidebar' })
  for (const group of ['Data', 'Operate', 'Admin']) {
    const section = within(sidebar).getByRole('region', { name: group })
    expect(within(section).queryAllByRole('listitem')).toHaveLength(0)
  }
})

test('shows who is logged in', async () => {
  render(<App />)

  expect(await screen.findByText('first.admin@harvester.test')).toBeInTheDocument()
  expect(fetch).toHaveBeenCalledWith('/api/me', expect.anything())
})
