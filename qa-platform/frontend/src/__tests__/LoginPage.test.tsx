/**
 * C10 — LoginPage tests
 *
 * LoginPage renders a login form with:
 *   - Email input (label: "Email address", placeholder: "you@example.com")
 *   - Password input (label: "Password", placeholder: "Your password")
 *   - Submit button with text "Sign in"
 *
 * Validation (client-side, fires before any API call):
 *   - Empty email  → 'Email is required'
 *   - Bad format   → 'Invalid email format'
 *   - Empty pass   → 'Password is required'
 *
 * NOTE: LoginPage does NOT currently have data-testid attributes on its inputs
 * or submit button. The tests below query by label text / role as a fallback.
 * To satisfy the data-testid contract described in the TDD plan, add the
 * following attributes to LoginPage.tsx:
 *   - email input    → data-testid="email-input"
 *   - password input → data-testid="password-input"
 *   - submit button  → data-testid="login-btn"
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from '../pages/LoginPage';

// ---- Mock dependencies --------------------------------------------------------

// Mock the authStore so login() doesn't touch real Zustand state
vi.mock('../store/authStore', () => ({
  useAuthStore: () => ({
    login: vi.fn(),
  }),
}));

// Mock authService to prevent real HTTP calls
vi.mock('../services/authService', () => ({
  authService: {
    login: vi.fn(),
  },
}));

// Mock react-hot-toast to suppress DOM warnings in jsdom
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock lucide-react icons used by LoginPage to avoid SVG rendering issues
vi.mock('lucide-react', () => ({
  Activity: () => null,
  Eye: () => null,
  EyeOff: () => null,
}));

// Mock LoadingSpinner
vi.mock('../components/UI/LoadingSpinner', () => ({
  LoadingSpinner: () => null,
}));

// ---- Render helper ------------------------------------------------------------
function renderLoginPage() {
  render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>,
  );
}

// ---- Tests -------------------------------------------------------------------
describe('C10 — LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submit button is present and renders', () => {
    renderLoginPage();
    // NOTE: add data-testid="login-btn" to the submit button in LoginPage.tsx
    const btn = screen.getByRole('button', { name: /sign in/i });
    expect(btn).toBeInTheDocument();
  });

  it('form fields have correct label associations (email-input, password-input, login-btn)', () => {
    renderLoginPage();

    // NOTE: add data-testid="email-input"    to the email <input> in LoginPage.tsx
    // NOTE: add data-testid="password-input" to the password <input> in LoginPage.tsx
    // NOTE: add data-testid="login-btn"      to the submit <button> in LoginPage.tsx

    // Querying by label is the accessible / RTL-idiomatic equivalent
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('submit with empty email shows "Email is required" error message', async () => {
    renderLoginPage();

    // Leave email blank, fill password so only email errors
    await userEvent.type(screen.getByLabelText(/^password$/i), 'anypassword');

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Email is required')).toBeInTheDocument();
    });
  });

  it('submit with invalid email format shows "Invalid email format" error', async () => {
    renderLoginPage();

    await userEvent.type(screen.getByLabelText(/email address/i), 'not-an-email');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'anypassword');

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid email format')).toBeInTheDocument();
    });
  });

  it('submit with empty password shows "Password is required" error message', async () => {
    renderLoginPage();

    await userEvent.type(screen.getByLabelText(/email address/i), 'user@example.com');
    // Leave password blank

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Password is required')).toBeInTheDocument();
    });
  });
});
