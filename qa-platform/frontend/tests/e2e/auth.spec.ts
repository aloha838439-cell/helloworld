import { test, expect } from '@playwright/test';

/**
 * Sprint 1 — 인증 플로우 E2E 시나리오
 *
 * 전제 조건:
 *   - frontend dev server: http://localhost:3000  (npm run dev)
 *   - backend API server:  http://localhost:8000  (docker-compose up)
 *
 * data-testid 요구 사항 (컴포넌트에 추가 필요):
 *   LoginPage.tsx    → email-input, password-input, login-btn, error-message
 *   RegisterPage.tsx → email-input, password-input, name-input, register-btn, success-toast
 *   Sidebar.tsx      → sidebar, logout-btn
 */

test.describe('인증 플로우', () => {

  /**
   * TC-01: 회원가입 성공 후 로그인 페이지로 이동
   *
   * Steps:
   *   1. /register 접속
   *   2. 이메일, 비밀번호, 이름 입력
   *   3. 회원가입 버튼 클릭
   * Expected:
   *   - URL이 /login으로 변경된다
   *   - "회원가입 완료" 성공 토스트가 표시된다
   *
   * NOTE: RegisterPage.tsx 수정 필요
   *   - email input    → data-testid="email-input"
   *   - password input → data-testid="password-input"
   *   - username input → data-testid="name-input"
   *   - submit button  → data-testid="register-btn"
   *   - 성공 후 navigate('/login') 으로 변경 (현재 /dashboard 이동)
   *   - toast.success 메시지에 "회원가입 완료" 포함 필요
   *   - toast 컨테이너에 data-testid="success-toast" 추가 필요
   */
  test('회원가입 성공 후 로그인 페이지로 이동', async ({ page }) => {
    await page.goto('/register');

    await page.fill('[data-testid="email-input"]', 'qa-tester@example.com');
    await page.fill('[data-testid="password-input"]', 'SecurePass123!');
    await page.fill('[data-testid="name-input"]', 'QA 테스터');
    await page.click('[data-testid="register-btn"]');

    await expect(page).toHaveURL('/login');
    await expect(page.locator('[data-testid="success-toast"]')).toContainText('회원가입 완료');
  });

  /**
   * TC-02: 올바른 자격증명으로 로그인 성공
   *
   * Steps:
   *   1. /login 접속
   *   2. 올바른 이메일/비밀번호 입력
   *   3. 로그인 버튼 클릭
   * Expected:
   *   - URL이 /dashboard로 변경된다
   *   - 좌측 사이드바가 visible하다
   *
   * NOTE: LoginPage.tsx 수정 필요
   *   - email input    → data-testid="email-input"
   *   - password input → data-testid="password-input"
   *   - submit button  → data-testid="login-btn"
   * NOTE: Sidebar.tsx (Layout.tsx의 <aside>) 수정 필요
   *   - <aside> element → data-testid="sidebar"
   */
  test('올바른 자격증명으로 로그인 성공', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[data-testid="email-input"]', 'qa-tester@example.com');
    await page.fill('[data-testid="password-input"]', 'SecurePass123!');
    await page.click('[data-testid="login-btn"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('[data-testid="sidebar"]')).toBeVisible();
  });

  /**
   * TC-03: 잘못된 비밀번호로 로그인 실패 — 에러 메시지 표시
   *
   * Steps:
   *   1. /login 접속
   *   2. 올바른 이메일 + 잘못된 비밀번호 입력
   *   3. 로그인 버튼 클릭
   * Expected:
   *   - "이메일 또는 비밀번호" 에러 메시지가 표시된다
   *   - URL이 /login으로 유지된다
   *
   * NOTE: LoginPage.tsx 수정 필요
   *   - 로그인 실패 에러 UI 요소 → data-testid="error-message"
   *   - 현재 toast.error()로만 처리 중. 인라인 에러 DOM 요소 추가 필요
   *     또는 toast 컨테이너에 data-testid="error-message" 추가
   */
  test('잘못된 비밀번호로 로그인 실패 — 에러 메시지 표시', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[data-testid="email-input"]', 'qa-tester@example.com');
    await page.fill('[data-testid="password-input"]', 'WrongPassword');
    await page.click('[data-testid="login-btn"]');

    await expect(page.locator('[data-testid="error-message"]')).toContainText('이메일 또는 비밀번호');
    await expect(page).toHaveURL('/login');
  });

  /**
   * TC-04: 미인증 사용자 보호 라우트 접근 시 /login 리다이렉트
   *
   * Steps:
   *   1. 로그인하지 않은 상태로 /analysis 직접 접근
   * Expected:
   *   - URL이 /login으로 리다이렉트된다
   *
   * NOTE: ProtectedRoute는 이미 구현됨 (src/components/Layout/ProtectedRoute.tsx)
   *   추가 data-testid 불필요
   */
  test('미인증 사용자 보호 라우트 접근 시 /login 리다이렉트', async ({ page }) => {
    await page.goto('/analysis');
    await expect(page).toHaveURL('/login');
  });

  /**
   * TC-05: 로그아웃 후 토큰 삭제 확인
   *
   * Steps:
   *   1. /login 접속 후 올바른 자격증명으로 로그인
   *   2. /dashboard 진입 확인
   *   3. 로그아웃 버튼 클릭
   *   4. URL /login 이동 확인
   *   5. localStorage의 'access_token' 키 null 확인
   * Expected:
   *   - 로그아웃 후 URL이 /login이다
   *   - localStorage.getItem('access_token')이 null이다
   *
   * NOTE: Sidebar.tsx (Layout.tsx 내 logout 버튼) 수정 필요
   *   - logout 버튼 → data-testid="logout-btn"
   *   - authStore.logout()은 이미 localStorage.removeItem('access_token') 호출
   *   - ROADMAP의 토큰 키가 'auth-token'이지만 authStore는 'access_token'을 사용함
   *     → 본 테스트는 실제 구현 기준인 'access_token' 키를 검증함
   */
  test('로그아웃 후 토큰 삭제 확인', async ({ page }) => {
    // 로그인 상태 셋업
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'qa-tester@example.com');
    await page.fill('[data-testid="password-input"]', 'SecurePass123!');
    await page.click('[data-testid="login-btn"]');
    await page.waitForURL('/dashboard');

    await page.click('[data-testid="logout-btn"]');
    await expect(page).toHaveURL('/login');

    // localStorage access_token 삭제 확인
    // (authStore.logout()은 localStorage.removeItem('access_token')을 호출)
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeNull();
  });

});
