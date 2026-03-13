/**
 * C10 — RegisterPage tests (register variant)
 *
 * RegisterPage renders a registration form with:
 *   - Email input
 *   - Username input
 *   - Password input (with live strength indicator)
 *   - Confirm Password input
 *   - Submit button "Create Account"
 *
 * Password strength logic (passwordStrength() function):
 *   Starts at 0, increments for each rule met:
 *     +1 if length >= 8
 *     +1 if contains uppercase letter
 *     +1 if contains digit
 *     +1 if contains special character
 *   Display: "Password strength: {strengthLabels[strength - 1]}"
 *   strengthLabels = ['Weak', 'Fair', 'Good', 'Strong']
 *
 * NOTE: The TDD plan specified Korean strength labels (약함/보통/강함), but the
 * actual RegisterPage implementation uses English labels:
 *   strength=1 → 'Weak'
 *   strength=2 → 'Fair'
 *   strength=3 → 'Good'
 *   strength=4 → 'Strong'
 * Tests are written to match the REAL implementation.
 *
 * On successful registration the component navigates to '/dashboard' (not '/login').
 *
 * NOTE: RegisterPage does NOT currently have data-testid attributes. Add them as needed.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import RegisterPage from '../pages/RegisterPage';
import { authService } from '../services/authService';

// ---- Mock dependencies --------------------------------------------------------

vi.mock('../store/authStore', () => ({
  useAuthStore: () => ({
    login: vi.fn(),
  }),
}));

vi.mock('../services/authService', () => ({
  authService: {
    register: vi.fn(),
  },
}));

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('lucide-react', () => ({
  Activity: () => null,
  Eye: () => null,
  EyeOff: () => null,
  CheckCircle: () => null,
}));

vi.mock('../components/UI/LoadingSpinner', () => ({
  LoadingSpinner: () => null,
}));

// ---- Render helpers ----------------------------------------------------------
function renderRegisterPage() {
  render(
    <MemoryRouter initialEntries={['/register']}>
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/dashboard" element={<div data-testid="dashboard-page">Dashboard</div>} />
        <Route path="/login" element={<div data-testid="login-page">Login</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

// ---- Tests -------------------------------------------------------------------
describe('C10 — RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---------- Password strength indicator tests --------------------------------

  it('password with length < 8 (only 1 criterion met: none) shows "Weak" strength indicator', async () => {
    renderRegisterPage();
    const passwordInput = screen.getByPlaceholderText(/at least 8 characters/i);

    // "abc" — length < 8, no uppercase, no digit, no special char → strength = 0
    // The indicator only appears when password is non-empty.
    // strength=0 means no rule met, display is "Too short" per the source:
    //   {strength > 0 ? strengthLabels[strength - 1] : 'Too short'}
    await userEvent.type(passwordInput, 'abc');

    await waitFor(() => {
      expect(screen.getByText(/password strength:/i)).toBeInTheDocument();
      expect(screen.getByText(/too short/i)).toBeInTheDocument();
    });
  });

  it('password meeting exactly 1 criterion (length >= 8 only) shows "Weak" strength indicator', async () => {
    renderRegisterPage();
    const passwordInput = screen.getByPlaceholderText(/at least 8 characters/i);

    // "abcdefgh" — length >= 8 (+1), no uppercase, no digit, no special → strength = 1 → "Weak"
    await userEvent.type(passwordInput, 'abcdefgh');

    await waitFor(() => {
      expect(screen.getByText(/password strength:.*weak/i)).toBeInTheDocument();
    });
  });

  it('password meeting 2 criteria shows "Fair" strength indicator', async () => {
    renderRegisterPage();
    const passwordInput = screen.getByPlaceholderText(/at least 8 characters/i);

    // "Abcdefgh" — length >= 8 (+1), uppercase (+1), no digit, no special → strength = 2 → "Fair"
    await userEvent.type(passwordInput, 'Abcdefgh');

    await waitFor(() => {
      expect(screen.getByText(/password strength:.*fair/i)).toBeInTheDocument();
    });
  });

  it('password meeting 3 criteria shows "Good" strength indicator', async () => {
    renderRegisterPage();
    const passwordInput = screen.getByPlaceholderText(/at least 8 characters/i);

    // "Abcdefg1" — length >= 8 (+1), uppercase (+1), digit (+1), no special → strength = 3 → "Good"
    await userEvent.type(passwordInput, 'Abcdefg1');

    await waitFor(() => {
      expect(screen.getByText(/password strength:.*good/i)).toBeInTheDocument();
    });
  });

  it('password meeting all 4 criteria shows "Strong" strength indicator', async () => {
    renderRegisterPage();
    const passwordInput = screen.getByPlaceholderText(/at least 8 characters/i);

    // "Abcdefg1!" — length >= 8 (+1), uppercase (+1), digit (+1), special (+1) → strength = 4 → "Strong"
    await userEvent.type(passwordInput, 'Abcdefg1!');

    await waitFor(() => {
      expect(screen.getByText(/password strength:.*strong/i)).toBeInTheDocument();
    });
  });

  // ---------- Validation error tests ------------------------------------------

  it('submit with empty username shows "Username is required" error', async () => {
    renderRegisterPage();

    await userEvent.type(screen.getByPlaceholderText(/you@example\.com/i), 'user@example.com');
    // Leave username blank
    await userEvent.type(screen.getByPlaceholderText(/at least 8 characters/i), 'Password1!');
    await userEvent.type(screen.getByPlaceholderText(/repeat your password/i), 'Password1!');

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText('Username is required')).toBeInTheDocument();
    });
  });

  it('submit with empty email shows "Email is required" error', async () => {
    renderRegisterPage();

    // Leave email blank; fill other fields correctly
    await userEvent.type(screen.getByPlaceholderText(/johndoe/i), 'validuser');
    await userEvent.type(screen.getByPlaceholderText(/at least 8 characters/i), 'Password1!');
    await userEvent.type(screen.getByPlaceholderText(/repeat your password/i), 'Password1!');

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText('Email is required')).toBeInTheDocument();
    });
  });

  // ---------- Successful registration test ------------------------------------

  it('successful registration navigates to /dashboard', async () => {
    const mockRegisterResponse = {
      access_token: 'mock.token.here',
      token_type: 'bearer',
      user: {
        id: 1,
        email: 'newuser@example.com',
        username: 'newuser',
        is_active: true,
        is_admin: false,
      },
    };

    vi.mocked(authService.register).mockResolvedValueOnce(mockRegisterResponse);

    renderRegisterPage();

    await userEvent.type(screen.getByPlaceholderText(/you@example\.com/i), 'newuser@example.com');
    await userEvent.type(screen.getByPlaceholderText(/johndoe/i), 'newuser');
    await userEvent.type(screen.getByPlaceholderText(/at least 8 characters/i), 'Password1!');
    await userEvent.type(screen.getByPlaceholderText(/repeat your password/i), 'Password1!');

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });
  });
});
