# Sprint 1 Playwright MCP 검증 보고서

> 날짜: 2026-03-13 | 대상 브랜치: sprint/s1

---

## 검증 범위

본 보고서는 Sprint 1 완료 조건 중 **Playwright E2E 검증** 파트를 다룬다.

| 항목 | 내용 |
|------|------|
| 검증 대상 | `frontend/tests/e2e/auth.spec.ts` 5개 시나리오 |
| 기준 문서 | `ROADMAP.md` §Sprint 1 검증, `docs/sprint/sprint1.md` |
| 기본 URL | `http://localhost:3000` |
| 검증 브라우저 | Chromium (Desktop Chrome), iPad Pro |
| 검토된 소스 파일 | LoginPage.tsx, RegisterPage.tsx, Sidebar.tsx (Layout.tsx), Header.tsx |
| 검토된 테스트 파일 | authStore.test.ts, ProtectedRoute.test.tsx, LoginPage.test.tsx, Sidebar.test.tsx |

---

## 파일 생성 결과

| 파일 경로 | 상태 | 비고 |
|----------|------|------|
| `frontend/playwright.config.ts` | 신규 생성 | ROADMAP.md 명세 기준 (webServer 블록 제외) |
| `frontend/tests/e2e/auth.spec.ts` | 신규 생성 | 5개 시나리오 완성 |
| `frontend/tests/e2e/fixtures/sample_defects.csv` | 신규 생성 | Sprint 2 결함 업로드 테스트용 fixture |

### playwright.config.ts 주요 설정

- `testDir`: `./tests/e2e`
- `fullyParallel`: `false` (DB 상태 공유로 순차 실행)
- `timeout`: 30,000ms
- `baseURL`: `http://localhost:3000`
- `projects`: chromium (Desktop Chrome), tablet (iPad Pro)
- `retries`: CI 환경에서 2회

> 참고: ROADMAP.md 원본에는 `webServer` 블록(docker-compose + npm run dev)이 포함되어 있으나,
> 과제 명세의 config 기준에는 포함되지 않아 생략하였다. 실제 CI 환경 구성 시 추가를 권장한다.

---

## data-testid 매핑 분석

ROADMAP.md Sprint 1 시나리오에서 요구하는 `data-testid` 목록을 실제 컴포넌트 소스와 대조하였다.

### LoginPage.tsx (`src/pages/LoginPage.tsx`)

| testid | 역할 | 컴포넌트 현황 |
|--------|------|------------|
| `email-input` | 이메일 입력 필드 | **누락** — `<input type="email">` 존재하나 `data-testid` 없음 |
| `password-input` | 비밀번호 입력 필드 | **누락** — `<input type="password">` 존재하나 `data-testid` 없음 |
| `login-btn` | 로그인 제출 버튼 | **누락** — `<button type="submit">` 존재하나 `data-testid` 없음 |
| `error-message` | 로그인 실패 에러 표시 | **누락** — 현재 `toast.error()`만 사용, 인라인 DOM 에러 요소 없음 |

### RegisterPage.tsx (`src/pages/RegisterPage.tsx`)

| testid | 역할 | 컴포넌트 현황 |
|--------|------|------------|
| `email-input` | 이메일 입력 필드 | **누락** — `<input type="email">` 존재하나 `data-testid` 없음 |
| `password-input` | 비밀번호 입력 필드 | **누락** — `<input type="password">` 존재하나 `data-testid` 없음 |
| `name-input` | 사용자명 입력 필드 | **누락** — `<input type="text">` (username 필드) 존재하나 `data-testid` 없음 |
| `register-btn` | 회원가입 제출 버튼 | **누락** — `<button type="submit">` 존재하나 `data-testid` 없음 |
| `success-toast` | 회원가입 완료 토스트 | **누락** — `toast.success()` 사용 중이나 DOM 요소에 `data-testid` 없음 |

추가 불일치: RegisterPage.tsx의 현재 로직은 성공 시 `/dashboard`로 이동하나,
TC-01 시나리오는 `/login` 이동을 기대한다. 네비게이션 대상 수정 필요.

또한 RegisterPage.tsx의 성공 토스트 메시지는 영문(`"Account created successfully."`)이나,
TC-01은 한국어 `"회원가입 완료"` 포함 여부를 검증한다. 메시지 수정 필요.

### Sidebar.tsx / Layout.tsx (`src/components/Layout/Sidebar.tsx`)

| testid | 역할 | 컴포넌트 현황 |
|--------|------|------------|
| `sidebar` | 사이드바 루트 요소 | **누락** — `<aside>` 요소 존재하나 `data-testid="sidebar"` 없음 |
| `logout-btn` | 로그아웃 버튼 | **누락** — `<button onClick={handleLogout}>` 존재하나 `data-testid` 없음 |

### Header.tsx (`src/components/Layout/Header.tsx`)

Sprint 1 E2E 시나리오에서 직접 검증하는 `data-testid`는 없음. 추가 변경 불필요.

---

## 시나리오별 검증 분석

### TC-01: 회원가입 성공 후 로그인 페이지로 이동

```
await page.fill('[data-testid="email-input"]', ...)    → 현재 실패 (testid 없음)
await page.fill('[data-testid="password-input"]', ...) → 현재 실패 (testid 없음)
await page.fill('[data-testid="name-input"]', ...)     → 현재 실패 (testid 없음)
await page.click('[data-testid="register-btn"]')       → 현재 실패 (testid 없음)
await expect(page).toHaveURL('/login')                 → 현재 실패 (/dashboard로 이동)
await expect(...success-toast).toContainText('회원가입 완료') → 현재 실패 (영문 메시지)
```

**실행 가능성**: 불가 (4개 testid 누락 + 2개 동작 불일치)
**필요 작업**: RegisterPage.tsx에 testid 추가, 성공 후 네비게이션을 `/login`으로 변경, 토스트 메시지 한국어 포함

---

### TC-02: 올바른 자격증명으로 로그인 성공

```
await page.fill('[data-testid="email-input"]', ...)    → 현재 실패 (testid 없음)
await page.fill('[data-testid="password-input"]', ...) → 현재 실패 (testid 없음)
await page.click('[data-testid="login-btn"]')          → 현재 실패 (testid 없음)
await expect(page).toHaveURL('/dashboard')             → 로직 정상 (navigate 구현됨)
await expect(...sidebar).toBeVisible()                 → 현재 실패 (testid 없음)
```

**실행 가능성**: 불가 (3개 testid 누락)
**필요 작업**: LoginPage.tsx에 `email-input`, `password-input`, `login-btn` testid 추가; Layout.tsx `<aside>`에 `sidebar` testid 추가

---

### TC-03: 잘못된 비밀번호로 로그인 실패 — 에러 메시지 표시

```
await page.fill('[data-testid="email-input"]', ...)    → 현재 실패 (testid 없음)
await page.fill('[data-testid="password-input"]', ...) → 현재 실패 (testid 없음)
await page.click('[data-testid="login-btn"]')          → 현재 실패 (testid 없음)
await expect(...error-message).toContainText('이메일 또는 비밀번호') → 현재 실패 (DOM 요소 없음)
await expect(page).toHaveURL('/login')                 → 로직 정상 (에러 시 페이지 유지)
```

**실행 가능성**: 불가 (3개 testid 누락 + 인라인 에러 요소 없음)
**필요 작업**: LoginPage.tsx 폼 제출 실패 시 `data-testid="error-message"` 인라인 에러 요소 렌더링 추가

---

### TC-04: 미인증 사용자 보호 라우트 접근 시 /login 리다이렉트

```
await page.goto('/analysis')
await expect(page).toHaveURL('/login')
```

**실행 가능성**: 가능 — ProtectedRoute 컴포넌트가 이미 구현되어 있으며 testid 불필요.
`src/components/Layout/ProtectedRoute.tsx`의 `isAuthenticated` 검사 로직이 정상 동작하면 즉시 통과 가능.

**주의**: 브라우저 localStorage에 이전 세션 토큰이 남아 있으면 리다이렉트가 발생하지 않을 수 있다. 테스트 실행 전 `storageState` 초기화 또는 `context.clearCookies()` 권장.

---

### TC-05: 로그아웃 후 토큰 삭제 확인

```
await page.click('[data-testid="logout-btn"]')  → 현재 실패 (testid 없음)
await expect(page).toHaveURL('/login')           → 로직 정상 (handleLogout 구현됨)
localStorage.getItem('access_token') === null   → 로직 정상 (authStore.logout() 구현됨)
```

**실행 가능성**: 불가 (1개 testid 누락)
**필요 작업**: Layout.tsx의 로그아웃 버튼에 `data-testid="logout-btn"` 추가

추가 사항: ROADMAP.md 원본 TC-05는 `localStorage.getItem('auth-token')`을 확인하나,
실제 authStore 구현(`authStore.test.ts` C8 기준)은 `access_token` 키를 사용한다.
본 `auth.spec.ts`는 실제 구현 기준인 `access_token`으로 작성하였다.

---

## 발견된 누락 data-testid 목록

컴포넌트에 즉시 추가가 필요한 `data-testid` 속성 목록이다.

### `src/pages/LoginPage.tsx`

| 요소 | 추가할 속성 |
|------|-----------|
| `<input type="email">` | `data-testid="email-input"` |
| `<input type="password">` | `data-testid="password-input"` |
| `<button type="submit">` (Sign in) | `data-testid="login-btn"` |
| 로그인 실패 에러 DOM 요소 (신규 추가) | `data-testid="error-message"` |

### `src/pages/RegisterPage.tsx`

| 요소 | 추가할 속성 | 추가 변경 사항 |
|------|-----------|-------------|
| `<input type="email">` | `data-testid="email-input"` | — |
| `<input type="text">` (username) | `data-testid="name-input"` | — |
| `<input type="password">` | `data-testid="password-input"` | — |
| `<button type="submit">` (Create Account) | `data-testid="register-btn"` | — |
| `toast.success()` 메시지 | `data-testid="success-toast"` | 메시지에 "회원가입 완료" 포함 필요 |
| `navigate('/dashboard', ...)` | — | `/login`으로 변경 필요 |

### `src/components/Layout/Sidebar.tsx` (실제 파일: Layout.tsx)

| 요소 | 추가할 속성 |
|------|-----------|
| `<aside>` 루트 요소 | `data-testid="sidebar"` |
| `<button onClick={handleLogout}>` (Sign out) | `data-testid="logout-btn"` |

---

## 단위 테스트와 E2E 테스트의 testid 불일치

`src/__tests__/LoginPage.test.tsx`의 주석(line 18-20)은 다음 사항을 명시적으로 기록하고 있다:

> "NOTE: LoginPage does NOT currently have data-testid attributes on its inputs
> or submit button. The tests below query by label text / role as a fallback."

즉 단위 테스트 파일 자체가 이미 누락을 인지하고 fallback 쿼리를 사용 중이다.
E2E 테스트는 fallback 없이 `data-testid` selector를 직접 사용하므로 컴포넌트 수정이 선행되어야 한다.

---

## 실행 명령어

```bash
# 특정 시나리오만 실행 (Sprint 1)
npx playwright test auth.spec.ts --project=chromium

# UI 모드로 디버깅
npx playwright test auth.spec.ts --ui

# 전체 E2E 실행
npx playwright test

# HTML 리포트 확인
npx playwright show-report
```

---

## 권장 사항

### 1순위 (TC-04 즉시 실행 가능화 완료 — 추가 작업 없음)

TC-04(미인증 리다이렉트)는 현재 구조에서 data-testid 없이도 실행 가능하다.
테스트 대상 서버 기동 후 바로 검증 시작 가능하다.

### 2순위 (단일 파일 수정으로 TC-02, TC-05 활성화)

`src/components/Layout/Sidebar.tsx`(`Layout.tsx`) 파일에 다음 두 속성을 추가하면
TC-02(로그인 성공 후 사이드바 확인)와 TC-05(로그아웃 토큰 삭제)가 즉시 실행 가능해진다:
- `<aside data-testid="sidebar">`
- `<button data-testid="logout-btn" onClick={handleLogout}>`

### 3순위 (단일 파일 수정으로 TC-03 활성화)

`src/pages/LoginPage.tsx`에 `email-input`, `password-input`, `login-btn` testid를 추가하고,
API 실패 시 렌더링되는 인라인 에러 요소(`data-testid="error-message"`)를 추가하면 TC-03이 활성화된다.

### 4순위 (TC-01 활성화 — 복수 변경 필요)

`src/pages/RegisterPage.tsx` 수정:
- testid 4개 추가 (`email-input`, `password-input`, `name-input`, `register-btn`)
- 성공 후 `navigate('/login', { replace: true })` 변경 (현재 `/dashboard`)
- `toast.success()` 메시지에 `"회원가입 완료"` 한국어 텍스트 포함
- `success-toast` testid 처리: react-hot-toast의 toast 컨테이너에 커스텀 testid를 부착하거나,
  `/login` 이동 후 쿼리 파라미터 또는 state로 토스트 메시지 전달 방식 고려 필요

### 5순위 (ROADMAP localStorage 키 불일치 해소)

ROADMAP.md TC-05의 `localStorage.getItem('auth-token')`은 실제 구현(`access_token`)과 다르다.
생성된 `auth.spec.ts`는 이미 실제 구현 기준(`access_token`)으로 수정되어 있다.
ROADMAP.md를 업데이트하거나 authStore 구현을 `auth-token`으로 통일하는 방향을 팀 내 결정 권장.

### 전반적 개선 사항

- `playwright.config.ts`에 `webServer` 블록 추가를 검토하여 CI에서 서버 자동 기동 지원
- 각 테스트 실행 전 `localStorage` 초기화를 위한 `test.beforeEach` 또는 `storageState: undefined` 설정 권장
- TC-01 회원가입 테스트는 동일 이메일 중복 등록 시 실패하므로 테스트용 계정 이메일에 `Date.now()` suffix 추가 고려
