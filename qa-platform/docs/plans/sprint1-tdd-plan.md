# Sprint 1 — 기반 인프라 + 인증 TDD 구현 계획

> **총 예상 시간**: 88h (22 SP) | **TDD 사이클 수**: 11개 | **대상 브랜치**: `sprint/s1`
> **테스트 위치**: `backend/tests/unit/`, `backend/tests/integration/`, `frontend/src/__tests__/`

---

## 타임라인 요약

| # | 사이클 | 대상 (ID) | Red | Green | Refactor | 소계 |
|---|--------|----------|-----|-------|----------|------|
| C1 | DB 모델 — User | S1-B1 | 3분 | 5분 | 2분 | 10분 |
| C2 | DB 모델 — Defect·Change·ImpactAnalysis·TestCase | S1-B1 | 4분 | 5분 | 3분 | 12분 |
| C3 | Alembic 마이그레이션 검증 | S1-B1 | 2분 | 3분 | 2분 | 7분 |
| C4 | 회원가입 API — 정상 경로 | S1-B2 | 4분 | 5분 | 3분 | 12분 |
| C5 | 회원가입 API — 중복·유효성 에러 | S1-B2 | 3분 | 4분 | 2분 | 9분 |
| C6 | 로그인 API — JWT 발급 | S1-B3 | 4분 | 5분 | 3분 | 12분 |
| C7 | /me 엔드포인트 — 토큰 검증 | S1-B4 | 3분 | 4분 | 2분 | 9분 |
| C8 | authStore — 토큰 저장·복원 | S1-F4 | 4분 | 5분 | 3분 | 12분 |
| C9 | ProtectedRoute — 리다이렉트 | S1-F5 | 3분 | 4분 | 2분 | 9분 |
| C10 | 로그인·회원가입 폼 유효성 | S1-F2/F3 | 4분 | 5분 | 3분 | 12분 |
| C11 | 사이드바 레이아웃 반응형 | S1-F6 | 3분 | 5분 | 2분 | 10분 |
| ✅ | **통합 E2E 체크포인트** | 전체 | — | — | — | 15분 |
| | **합계** | | | | | **~119분** |

> 사이클당 2~5분 단위이며, 실제 구현 반복(multiple passes) 포함 시 sprint 전체 공수에 수렴합니다.

---

## 사전 준비 (5분)

```bash
git checkout sprint/s1
cd qa-platform

# Python 가상환경
cd backend && python -m venv venv && source venv/Scripts/activate
pip install -r requirements.txt

# 테스트 DB 환경변수 설정 (.env.test)
echo "DATABASE_URL=postgresql://qauser:qapassword@localhost:5432/qadb_test" > .env.test
echo "SECRET_KEY=test-secret-key" >> .env.test

# 프론트엔드
cd ../frontend && npm install
```

---

## Cycle 1 — DB 모델: User

> **목표**: User 테이블 ORM 모델이 올바른 컬럼·제약조건을 갖는다.
> **대상 파일**: `backend/src/models/user.py`
> **소요 시간**: 10분

### 🔴 RED (3분)

**목표**: User 모델의 컬럼 구조를 검증하는 실패 테스트 작성

**파일**: `backend/tests/unit/test_models.py`

```python
import pytest
from sqlalchemy import inspect
from src.models.user import User
from src.models.base import Base
from sqlalchemy import create_engine

@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e

def test_user_table_columns(engine):
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("users")}
    assert {"id", "email", "hashed_password", "name", "role", "created_at"} <= columns

def test_user_email_unique(engine):
    inspector = inspect(engine)
    unique_constraints = inspector.get_unique_constraints("users")
    unique_cols = [c for uc in unique_constraints for c in uc["column_names"]]
    assert "email" in unique_cols

def test_user_role_default():
    user = User(email="test@test.com", hashed_password="hash", name="테스터")
    assert user.role == "qa_member"
```

**실행**:
```bash
cd backend && pytest tests/unit/test_models.py::test_user_table_columns -v
```

**예상 결과**: `FAILED — ImportError 또는 AssertionError (컬럼 미정의)`

---

### 🟢 GREEN (5분)

**목표**: User 모델 정의로 테스트 통과

**파일**: `backend/src/models/user.py` 확인 및 수정

```python
# 핵심 구조 확인 포인트
class User(Base):
    __tablename__ = "users"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email           = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name            = Column(String(100))
    role            = Column(String(50), default="qa_member")
    created_at      = Column(DateTime, default=datetime.utcnow)
```

**실행**:
```bash
pytest tests/unit/test_models.py -v
```

**예상 결과**: `3 passed`

---

### 🔵 REFACTOR (2분)

**개선 항목**:
- `role` 컬럼에 `CheckConstraint("role IN ('qa_member','qa_lead','admin')")` 추가
- `email` 컬럼 인덱스 추가 (`index=True`)

**실행**:
```bash
pytest tests/unit/test_models.py -v
```

**예상 결과**: `3 passed` (변경 없음)

---

## Cycle 2 — DB 모델: Defect · Change · ImpactAnalysis · TestCase

> **목표**: 나머지 4개 핵심 테이블이 스키마 명세대로 생성된다.
> **소요 시간**: 12분

### 🔴 RED (4분)

**파일**: `backend/tests/unit/test_models.py` (추가)

```python
def test_defect_table_columns(engine):
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("defects")}
    assert {"id", "title", "description", "severity",
            "reported_date", "status", "embedding"} <= columns

def test_impact_analysis_fk_to_changes(engine):
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys("impact_analyses")
    fk_cols = [fk["referred_table"] for fk in fks]
    assert "changes" in fk_cols

def test_test_case_fk_to_impact_analyses(engine):
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys("test_cases")
    fk_cols = [fk["referred_table"] for fk in fks]
    assert "impact_analyses" in fk_cols

def test_impact_score_precision(engine):
    inspector = inspect(engine)
    columns = inspector.get_columns("impact_analyses")
    score_col = next(c for c in columns if c["name"] == "impact_score")
    # DECIMAL(5,2) 확인
    assert hasattr(score_col["type"], "precision")
```

**실행**:
```bash
pytest tests/unit/test_models.py -v
```

**예상 결과**: `4 FAILED`

---

### 🟢 GREEN (5분)

모델 파일 4개(`defect.py`, `change.py`, `impact_analysis.py`, `test_case.py`)를 `Base.metadata`에 등록 확인.

**실행**:
```bash
pytest tests/unit/test_models.py -v
```

**예상 결과**: `7 passed`

---

### 🔵 REFACTOR (3분)

- `models/__init__.py`에서 모든 모델 일괄 import 확인
- `Defect.embedding` 컬럼 타입을 `JSON`으로 명시적 선언

**실행**:
```bash
pytest tests/unit/test_models.py -v
```

**예상 결과**: `7 passed`

---

## Cycle 3 — Alembic 마이그레이션 검증

> **목표**: `alembic upgrade head` 가 실제 PostgreSQL에 오류 없이 적용된다.
> **소요 시간**: 7분

### 🔴 RED (2분)

**파일**: `backend/tests/integration/test_migrations.py`

```python
import subprocess, pytest

def test_alembic_upgrade_head():
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd="backend"
    )
    assert result.returncode == 0, f"Migration failed:\n{result.stderr}"

def test_all_tables_exist(db_session):
    from sqlalchemy import inspect
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()
    for table in ["users", "defects", "changes", "impact_analyses", "test_cases"]:
        assert table in tables, f"Missing table: {table}"
```

**실행**:
```bash
pytest tests/integration/test_migrations.py -v
```

**예상 결과**: `FAILED — alembic.ini 또는 env.py 설정 미완`

---

### 🟢 GREEN (3분)

`alembic.ini`의 `sqlalchemy.url`을 `.env` 환경변수로 연결:

```ini
# alembic.ini
sqlalchemy.url = %(DATABASE_URL)s
```

**실행**:
```bash
alembic upgrade head
pytest tests/integration/test_migrations.py -v
```

**예상 결과**: `2 passed`

---

### 🔵 REFACTOR (2분)

- `alembic downgrade -1` → `alembic upgrade head` 왕복 테스트로 멱등성 확인

**실행**:
```bash
pytest tests/integration/test_migrations.py -v
```

**예상 결과**: `2 passed`

---

## Cycle 4 — 회원가입 API: 정상 경로

> **목표**: `POST /api/auth/register` 가 201을 반환하고 비밀번호를 bcrypt로 저장한다.
> **소요 시간**: 12분

### 🔴 RED (4분)

**파일**: `backend/tests/integration/test_auth_api.py`

```python
import pytest
from fastapi.testclient import TestClient
from src.main import app
from passlib.context import CryptContext

client = TestClient(app)
pwd_context = CryptContext(schemes=["bcrypt"])

def test_register_success():
    res = client.post("/api/auth/register", json={
        "email": "new@example.com",
        "password": "SecurePass123!",
        "name": "신규사용자"
    })
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "new@example.com"
    assert "hashed_password" not in body          # 비밀번호 응답 노출 금지

def test_register_password_is_hashed(db_session):
    from src.models.user import User
    user = db_session.query(User).filter_by(email="new@example.com").first()
    assert user is not None
    assert pwd_context.verify("SecurePass123!", user.hashed_password)
    assert user.hashed_password != "SecurePass123!"
```

**실행**:
```bash
pytest tests/integration/test_auth_api.py::test_register_success -v
```

**예상 결과**: `FAILED — 404 또는 422`

---

### 🟢 GREEN (5분)

`backend/src/app/routers/auth.py` register 엔드포인트 구현 확인:
- bcrypt 해싱 적용
- 응답에서 `hashed_password` 필드 제외 (`response_model` 사용)

**실행**:
```bash
pytest tests/integration/test_auth_api.py -k "register" -v
```

**예상 결과**: `2 passed`

---

### 🔵 REFACTOR (3분)

- `UserCreate` / `UserResponse` Pydantic 스키마 분리 확인
- `password` 필드 최소 8자 `Field(min_length=8)` 제약 추가

**실행**:
```bash
pytest tests/integration/test_auth_api.py -k "register" -v
```

**예상 결과**: `2 passed`

---

## Cycle 5 — 회원가입 API: 중복 · 유효성 에러

> **목표**: 중복 이메일 409, 잘못된 입력 422를 반환한다.
> **소요 시간**: 9분

### 🔴 RED (3분)

```python
def test_register_duplicate_email():
    # 동일 이메일 두 번 등록
    payload = {"email": "dup@example.com", "password": "Pass1234!", "name": "중복"}
    client.post("/api/auth/register", json=payload)
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 409
    assert "already" in res.json()["detail"].lower()

def test_register_short_password():
    res = client.post("/api/auth/register", json={
        "email": "short@example.com",
        "password": "abc",
        "name": "짧은비번"
    })
    assert res.status_code == 422

def test_register_invalid_email():
    res = client.post("/api/auth/register", json={
        "email": "not-an-email",
        "password": "Pass1234!",
        "name": "잘못된이메일"
    })
    assert res.status_code == 422
```

**실행**:
```bash
pytest tests/integration/test_auth_api.py -k "duplicate or short or invalid" -v
```

**예상 결과**: `3 FAILED`

---

### 🟢 GREEN (4분)

라우터에서 중복 이메일 체크 후 `HTTPException(status_code=409)` 발생 확인.
Pydantic `EmailStr` 타입으로 이메일 유효성 자동 처리.

**실행**:
```bash
pytest tests/integration/test_auth_api.py -v
```

**예상 결과**: `5 passed`

---

### 🔵 REFACTOR (2분)

- 에러 메시지 한국어로 통일 (`"이미 사용 중인 이메일입니다."`)
- 에러 응답 스키마 `{"detail": "..."}` 형식 일관성 확인

**실행**:
```bash
pytest tests/integration/test_auth_api.py -v
```

**예상 결과**: `5 passed`

---

## Cycle 6 — 로그인 API: JWT 발급

> **목표**: `POST /api/auth/login` 이 유효한 JWT를 반환하고, 잘못된 자격증명은 401을 반환한다.
> **소요 시간**: 12분

### 🔴 RED (4분)

**파일**: `backend/tests/integration/test_auth_api.py` (추가)

```python
from jose import jwt as jose_jwt
import os

def test_login_success_returns_jwt():
    # 사전: 사용자 등록
    client.post("/api/auth/register", json={
        "email": "login@example.com", "password": "Pass1234!", "name": "로그인테스터"
    })
    res = client.post("/api/auth/login", json={
        "email": "login@example.com", "password": "Pass1234!"
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    assert token is not None

    payload = jose_jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
    assert "sub" in payload
    assert payload["sub"] != ""

def test_login_jwt_expires_in_30min():
    client.post("/api/auth/register", json={
        "email": "expiry@example.com", "password": "Pass1234!", "name": "만료테스터"
    })
    res = client.post("/api/auth/login", json={
        "email": "expiry@example.com", "password": "Pass1234!"
    })
    token = res.json()["access_token"]
    payload = jose_jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
    import time
    remaining = payload["exp"] - time.time()
    assert 1700 < remaining < 1900  # 약 30분 (1800초 ± 100초)

def test_login_wrong_password_returns_401():
    res = client.post("/api/auth/login", json={
        "email": "login@example.com", "password": "WrongPass!"
    })
    assert res.status_code == 401

def test_login_nonexistent_user_returns_401():
    res = client.post("/api/auth/login", json={
        "email": "ghost@example.com", "password": "Pass1234!"
    })
    assert res.status_code == 401
```

**실행**:
```bash
pytest tests/integration/test_auth_api.py -k "login" -v
```

**예상 결과**: `4 FAILED`

---

### 🟢 GREEN (5분)

`auth.py` JWT 발급 로직 확인:
- `python-jose` + `HS256` 알고리즘
- `exp` 클레임 = `now + timedelta(minutes=30)`
- `sub` 클레임 = `str(user.id)`

**실행**:
```bash
pytest tests/integration/test_auth_api.py -k "login" -v
```

**예상 결과**: `4 passed`

---

### 🔵 REFACTOR (3분)

- `create_access_token()` 함수를 `app/auth.py`로 분리하여 재사용성 확보
- `token_type: "bearer"` 응답 필드 포함 확인

**실행**:
```bash
pytest tests/integration/test_auth_api.py -v
```

**예상 결과**: `9 passed`

---

## Cycle 7 — /me 엔드포인트: Bearer 토큰 검증

> **목표**: 유효 토큰 → 사용자 정보 반환, 만료·위조 토큰 → 401.
> **소요 시간**: 9분

### 🔴 RED (3분)

```python
def test_me_with_valid_token():
    # 로그인으로 토큰 획득
    client.post("/api/auth/register", json={
        "email": "me@example.com", "password": "Pass1234!", "name": "미테스터"
    })
    login_res = client.post("/api/auth/login", json={
        "email": "me@example.com", "password": "Pass1234!"
    })
    token = login_res.json()["access_token"]

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "me@example.com"
    assert "hashed_password" not in res.json()

def test_me_with_expired_token():
    from jose import jwt as jose_jwt
    import time
    expired_token = jose_jwt.encode(
        {"sub": "fake-id", "exp": time.time() - 1},
        os.getenv("SECRET_KEY"), algorithm="HS256"
    )
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401

def test_me_without_token():
    res = client.get("/api/auth/me")
    assert res.status_code == 401
```

**실행**:
```bash
pytest tests/integration/test_auth_api.py -k "me" -v
```

**예상 결과**: `3 FAILED`

---

### 🟢 GREEN (4분)

`get_current_user` 의존성 주입 함수가 `Authorization` 헤더를 파싱하고, 토큰 검증 실패 시 `HTTPException(401)` 발생 확인.

**실행**:
```bash
pytest tests/integration/test_auth_api.py -k "me" -v
```

**예상 결과**: `3 passed`

---

### 🔵 REFACTOR (2분)

- `get_current_user` → `Depends(get_current_user)` 패턴 일관 적용
- 에러 메시지 `"유효하지 않은 인증 토큰입니다."` 한국어 통일

**실행**:
```bash
pytest tests/integration/test_auth_api.py -v
```

**예상 결과**: `12 passed`

---

## ✅ 백엔드 체크포인트 (5분)

```bash
# 전체 백엔드 테스트 일괄 실행
cd backend && pytest tests/ -v --tb=short

# 예상: 12+ passed, 0 failed
# 커버리지 확인
pytest tests/ --cov=src/app --cov-report=term-missing
# 목표: auth 모듈 커버리지 ≥ 70%
```

---

## Cycle 8 — authStore: 토큰 저장 · 복원

> **목표**: Zustand store가 토큰을 localStorage에 영속하고, 새로고침 후 복원한다.
> **대상 파일**: `frontend/src/store/authStore.ts`
> **소요 시간**: 12분

### 🔴 RED (4분)

**파일**: `frontend/src/__tests__/authStore.test.ts`

```typescript
import { renderHook, act } from '@testing-library/react';
import { useAuthStore } from '../store/authStore';

// localStorage mock
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, val: string) => { store[key] = val; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

beforeEach(() => localStorageMock.clear());

test('login()이 토큰을 store와 localStorage에 저장한다', () => {
  const { result } = renderHook(() => useAuthStore());
  act(() => result.current.login('test-token', { id: '1', email: 'a@b.com', name: '테스터', role: 'qa_member' }));

  expect(result.current.token).toBe('test-token');
  expect(localStorageMock.getItem('auth-token')).toBe('test-token');
});

test('logout()이 토큰을 store와 localStorage에서 제거한다', () => {
  const { result } = renderHook(() => useAuthStore());
  act(() => result.current.login('test-token', { id: '1', email: 'a@b.com', name: '테스터', role: 'qa_member' }));
  act(() => result.current.logout());

  expect(result.current.token).toBeNull();
  expect(localStorageMock.getItem('auth-token')).toBeNull();
});

test('새로고침 후 localStorage에서 토큰을 복원한다', () => {
  localStorageMock.setItem('auth-token', 'persisted-token');
  const { result } = renderHook(() => useAuthStore());
  // Zustand persist middleware가 초기화 시 localStorage 읽음
  expect(result.current.token).toBe('persisted-token');
});
```

**실행**:
```bash
cd frontend && npm test -- --testPathPattern=authStore
```

**예상 결과**: `3 FAILED`

---

### 🟢 GREEN (5분)

`authStore.ts`에 Zustand `persist` 미들웨어 적용 확인:

```typescript
// 핵심 구조 확인 포인트
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      login: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: 'auth-token' }
  )
);
```

**실행**:
```bash
npm test -- --testPathPattern=authStore
```

**예상 결과**: `3 passed`

---

### 🔵 REFACTOR (3분)

- `isAuthenticated` 파생 상태 셀렉터 추가: `token !== null`
- `user` 타입을 `User | null`로 명시

**실행**:
```bash
npm test -- --testPathPattern=authStore
```

**예상 결과**: `3 passed`

---

## Cycle 9 — ProtectedRoute: 미인증 리다이렉트

> **목표**: 인증되지 않은 사용자가 보호 경로 접근 시 `/login`으로 리다이렉트된다.
> **소요 시간**: 9분

### 🔴 RED (3분)

**파일**: `frontend/src/__tests__/ProtectedRoute.test.tsx`

```typescript
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from '../components/Layout/ProtectedRoute';
import { useAuthStore } from '../store/authStore';

jest.mock('../store/authStore');
const mockUseAuthStore = useAuthStore as jest.Mock;

test('미인증 사용자는 /login으로 리다이렉트된다', () => {
  mockUseAuthStore.mockReturnValue({ token: null });

  render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/login" element={<div>로그인 페이지</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>대시보드</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );

  expect(screen.getByText('로그인 페이지')).toBeInTheDocument();
  expect(screen.queryByText('대시보드')).not.toBeInTheDocument();
});

test('인증된 사용자는 보호 경로에 접근할 수 있다', () => {
  mockUseAuthStore.mockReturnValue({ token: 'valid-token' });

  render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/login" element={<div>로그인 페이지</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>대시보드</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );

  expect(screen.getByText('대시보드')).toBeInTheDocument();
  expect(screen.queryByText('로그인 페이지')).not.toBeInTheDocument();
});
```

**실행**:
```bash
npm test -- --testPathPattern=ProtectedRoute
```

**예상 결과**: `2 FAILED`

---

### 🟢 GREEN (4분)

```typescript
// ProtectedRoute.tsx 핵심 구조
export const ProtectedRoute = () => {
  const { token } = useAuthStore();
  return token ? <Outlet /> : <Navigate to="/login" replace />;
};
```

**실행**:
```bash
npm test -- --testPathPattern=ProtectedRoute
```

**예상 결과**: `2 passed`

---

### 🔵 REFACTOR (2분)

- 로그인 후 원래 경로 복원: `<Navigate to="/login" state={{ from: location }} replace />`

**실행**:
```bash
npm test -- --testPathPattern=ProtectedRoute
```

**예상 결과**: `2 passed`

---

## Cycle 10 — 로그인 · 회원가입 폼 유효성 검사

> **목표**: 빈 값·형식 오류 시 인라인 에러 메시지가 표시되고, 유효한 입력 시 API를 호출한다.
> **소요 시간**: 12분

### 🔴 RED (4분)

**파일**: `frontend/src/__tests__/LoginPage.test.tsx`

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from '../pages/LoginPage';

const renderLogin = () => render(
  <MemoryRouter><LoginPage /></MemoryRouter>
);

test('이메일 빈값 제출 시 에러 메시지 표시', async () => {
  renderLogin();
  fireEvent.click(screen.getByTestId('login-btn'));
  expect(await screen.findByText(/이메일을 입력/i)).toBeInTheDocument();
});

test('잘못된 이메일 형식 에러 표시', async () => {
  renderLogin();
  await userEvent.type(screen.getByTestId('email-input'), 'not-an-email');
  fireEvent.click(screen.getByTestId('login-btn'));
  expect(await screen.findByText(/유효한 이메일/i)).toBeInTheDocument();
});

test('비밀번호 빈값 제출 시 에러 메시지 표시', async () => {
  renderLogin();
  await userEvent.type(screen.getByTestId('email-input'), 'test@test.com');
  fireEvent.click(screen.getByTestId('login-btn'));
  expect(await screen.findByText(/비밀번호를 입력/i)).toBeInTheDocument();
});

test('유효한 입력 시 login 버튼 활성화', async () => {
  renderLogin();
  await userEvent.type(screen.getByTestId('email-input'), 'test@test.com');
  await userEvent.type(screen.getByTestId('password-input'), 'Pass1234!');
  expect(screen.getByTestId('login-btn')).not.toBeDisabled();
});
```

**실행**:
```bash
npm test -- --testPathPattern=LoginPage
```

**예상 결과**: `4 FAILED`

---

### 🟢 GREEN (5분)

`LoginPage.tsx`에 `react-hook-form` + `data-testid` 속성 확인:
- `register('email', { required: '이메일을 입력해주세요.', pattern: { value: /\S+@\S+/, message: '유효한 이메일을 입력해주세요.' } })`
- `register('password', { required: '비밀번호를 입력해주세요.' })`

**실행**:
```bash
npm test -- --testPathPattern=LoginPage
```

**예상 결과**: `4 passed`

---

### 🔵 REFACTOR (3분)

- 회원가입 페이지 동일 패턴 적용 확인 (`RegisterPage.test.tsx` 추가)
- 비밀번호 강도 표시: 8자 미만 → "약함", 8~12자 → "보통", 12자 이상 → "강함"

**실행**:
```bash
npm test -- --testPathPattern="LoginPage|RegisterPage"
```

**예상 결과**: `8 passed`

---

## Cycle 11 — 사이드바 레이아웃: 반응형 검증

> **목표**: 데스크톱(1280px)에서 사이드바가 보이고, 태블릿(768px)에서 숨김 처리된다.
> **소요 시간**: 10분

### 🔴 RED (3분)

**파일**: `frontend/src/__tests__/Sidebar.test.tsx`

```typescript
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '../components/Layout/Sidebar';

const renderSidebar = () => render(
  <MemoryRouter><Sidebar /></MemoryRouter>
);

test('사이드바에 주요 네비게이션 링크가 있다', () => {
  renderSidebar();
  expect(screen.getByText(/대시보드/i)).toBeInTheDocument();
  expect(screen.getByText(/분석/i)).toBeInTheDocument();
  expect(screen.getByText(/결함/i)).toBeInTheDocument();
});

test('현재 경로에 해당하는 메뉴 항목이 활성화된다', () => {
  render(
    <MemoryRouter initialEntries={['/analysis']}>
      <Sidebar />
    </MemoryRouter>
  );
  const analysisLink = screen.getByTestId('nav-analysis');
  expect(analysisLink).toHaveClass('active'); // 또는 aria-current="page"
});

test('사이드바는 data-testid="sidebar"를 가진다', () => {
  renderSidebar();
  expect(screen.getByTestId('sidebar')).toBeInTheDocument();
});
```

**실행**:
```bash
npm test -- --testPathPattern=Sidebar
```

**예상 결과**: `3 FAILED`

---

### 🟢 GREEN (5분)

`Sidebar.tsx`에 `data-testid="sidebar"` 속성 추가 확인, `useLocation()` 으로 활성 경로 감지.

**실행**:
```bash
npm test -- --testPathPattern=Sidebar
```

**예상 결과**: `3 passed`

---

### 🔵 REFACTOR (2분)

- 네비게이션 항목을 `NAV_ITEMS` 배열로 추출 (확장성)
- `aria-current="page"` 접근성 속성 추가

**실행**:
```bash
npm test -- --testPathPattern=Sidebar
```

**예상 결과**: `3 passed`

---

## ✅ 최종 통합 체크포인트 (15분)

### 전체 테스트 일괄 실행

```bash
# Backend
cd backend
pytest tests/ -v --tb=short --cov=src --cov-report=term-missing
# 목표: 모든 테스트 passed, auth 모듈 커버리지 ≥ 70%

# Frontend
cd ../frontend
npm test -- --coverage --watchAll=false
# 목표: 모든 테스트 passed

# Playwright E2E (서비스 기동 후)
docker-compose up -d
npx playwright test auth.spec.ts --project=chromium
# 목표: 5개 시나리오 passed
```

### Docker Compose 통합 검증

```bash
docker-compose up --build -d
curl http://localhost:8000/docs          # Swagger UI 접근 확인
curl http://localhost:3000               # React 앱 접근 확인
docker-compose ps                        # 3개 서비스 모두 Up 상태
```

---

## 완료 기준 (Definition of Done) 체크리스트

### Backend
- [ ] `test_user_table_columns` PASS
- [ ] `test_alembic_upgrade_head` PASS
- [ ] `test_register_success` PASS
- [ ] `test_register_duplicate_email` → 409 PASS
- [ ] `test_login_success_returns_jwt` PASS — `sub=user_id` 확인
- [ ] `test_login_jwt_expires_in_30min` PASS
- [ ] `test_login_wrong_password_returns_401` PASS
- [ ] `test_me_with_valid_token` PASS
- [ ] `test_me_with_expired_token` → 401 PASS
- [ ] auth 모듈 커버리지 ≥ 70%

### Frontend
- [ ] `authStore` — login/logout/persist 3 테스트 PASS
- [ ] `ProtectedRoute` — 미인증 리다이렉트 / 인증 접근 2 테스트 PASS
- [ ] `LoginPage` — 유효성 검사 4 테스트 PASS
- [ ] `Sidebar` — 네비게이션 / 활성 메뉴 3 테스트 PASS

### E2E (Playwright)
- [ ] `auth.spec.ts` 5개 시나리오 PASS (Chromium)
- [ ] `docker-compose up` 3개 서비스 정상 기동

---

*작성일: 2026-03-13 | 스킬: writing-plans | 대상: sprint/s1*
