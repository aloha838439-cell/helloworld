/**
 * C9 — ProtectedRoute tests
 *
 * ProtectedRoute reads isAuthenticated from useAuthStore.
 * When unauthenticated it renders <Navigate to="/login" state={{ from: location }} replace />.
 * When authenticated it renders its children.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import ProtectedRoute from '../components/Layout/ProtectedRoute';

// ---- Mock the authStore --------------------------------------------------------
// We mock the entire module and override isAuthenticated per test.
const mockUseAuthStore = vi.fn();

vi.mock('../store/authStore', () => ({
  useAuthStore: () => mockUseAuthStore(),
}));

// ---- Helper component that exposes the current location for assertions --------
function LocationDisplay() {
  const location = useLocation();
  return (
    <div>
      <span data-testid="pathname">{location.pathname}</span>
      <span data-testid="from-state">
        {(location.state as { from?: { pathname: string } })?.from?.pathname ?? ''}
      </span>
    </div>
  );
}

// ---- Render helper ------------------------------------------------------------
function renderWithRouter(
  initialEntries: string[],
  isAuthenticated: boolean,
) {
  mockUseAuthStore.mockReturnValue({ isAuthenticated });

  render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        {/* The protected resource */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div data-testid="protected-content">Protected Content</div>
            </ProtectedRoute>
          }
        />
        {/* Login page captures where we ended up + the state passed */}
        <Route path="/login" element={<LocationDisplay />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('C9 — ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('unauthenticated user is redirected to /login', () => {
    renderWithRouter(['/dashboard'], false);

    // We should now be on /login
    expect(screen.getByTestId('pathname').textContent).toBe('/login');
    // Protected content must NOT be visible
    expect(screen.queryByTestId('protected-content')).toBeNull();
  });

  it('authenticated user can access protected route content', () => {
    renderWithRouter(['/dashboard'], true);

    // Protected content must be rendered
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    // We must NOT have been redirected to login
    expect(screen.queryByTestId('pathname')).toBeNull();
  });

  it('redirect preserves the original location in state', () => {
    // Start at /dashboard while unauthenticated → redirect → check state.from
    renderWithRouter(['/dashboard'], false);

    // ProtectedRoute passes state={{ from: location }} to Navigate.
    // The <LocationDisplay> at /login reads location.state.from.pathname.
    expect(screen.getByTestId('from-state').textContent).toBe('/dashboard');
  });
});
