/**
 * C8 — authStore tests
 *
 * Tests cover the Zustand authStore with localStorage persistence.
 * The store uses zustand/persist with key 'qa-auth-store'.
 * login() also manually calls localStorage.setItem('access_token', token).
 * logout() calls localStorage.removeItem for 'access_token' and 'user'.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '../store/authStore';
import type { User } from '../types';

// Helper: reset the Zustand store to its initial state between tests.
// useAuthStore.setState is available on every Zustand store instance.
const resetStore = () => {
  useAuthStore.setState({
    token: null,
    user: null,
    isAuthenticated: false,
  });
};

const mockUser: User = {
  id: 1,
  email: 'test@example.com',
  username: 'testuser',
  is_active: true,
  is_admin: false,
};

const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature';

describe('C8 — authStore', () => {
  beforeEach(() => {
    // Clear localStorage and reset store state before each test.
    localStorage.clear();
    resetStore();
  });

  it('initial state has token=null and user=null', () => {
    const { token, user } = useAuthStore.getState();
    expect(token).toBeNull();
    expect(user).toBeNull();
  });

  it('isAuthenticated is false when no token exists in initial state', () => {
    const { isAuthenticated } = useAuthStore.getState();
    expect(isAuthenticated).toBe(false);
  });

  it('login() stores token and user in state', () => {
    useAuthStore.getState().login(mockToken, mockUser);

    const { token, user } = useAuthStore.getState();
    expect(token).toBe(mockToken);
    expect(user).toEqual(mockUser);
  });

  it('login() sets isAuthenticated to true', () => {
    useAuthStore.getState().login(mockToken, mockUser);

    const { isAuthenticated } = useAuthStore.getState();
    expect(isAuthenticated).toBe(true);
  });

  it('login() persists token to localStorage under access_token key', () => {
    useAuthStore.getState().login(mockToken, mockUser);

    expect(localStorage.getItem('access_token')).toBe(mockToken);
  });

  it('isAuthenticated is true when token exists after login', () => {
    useAuthStore.getState().login(mockToken, mockUser);

    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it('logout() clears token and user from state', () => {
    // Arrange: log in first
    useAuthStore.getState().login(mockToken, mockUser);

    // Act
    useAuthStore.getState().logout();

    const { token, user } = useAuthStore.getState();
    expect(token).toBeNull();
    expect(user).toBeNull();
  });

  it('logout() sets isAuthenticated to false', () => {
    useAuthStore.getState().login(mockToken, mockUser);
    useAuthStore.getState().logout();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it('logout() removes access_token from localStorage', () => {
    useAuthStore.getState().login(mockToken, mockUser);
    // Verify it was set
    expect(localStorage.getItem('access_token')).toBe(mockToken);

    useAuthStore.getState().logout();

    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('logout() removes user key from localStorage', () => {
    // The logout() implementation calls localStorage.removeItem('user').
    // Manually set the key to confirm removal.
    localStorage.setItem('user', JSON.stringify(mockUser));
    useAuthStore.getState().login(mockToken, mockUser);

    useAuthStore.getState().logout();

    expect(localStorage.getItem('user')).toBeNull();
  });
});
