# Sprint 1 코드 리뷰 보고서

> 리뷰어: code-reviewer subagent | 날짜: 2026-03-13 | PR: #1

---

## 요약 스코어카드

| 영역 | 점수 | 등급 |
|------|------|------|
| TDD 원칙 준수 | 6/10 | 🟡 |
| 테스트 독립성 | 6/10 | 🟡 |
| 커버리지 충분성 | 7/10 | 🟡 |
| 보안 | 7/10 | 🟡 |
| 코드 품질 | 8/10 | 🟢 |
| **종합** | **6.8/10** | 🟡 |

---

## 🔴 Critical (즉시 수정 필요)

### C-01. `conftest.py` — 파일 기반 SQLite DB로 테스트 간 오염 위험

**파일**: `backend/tests/conftest.py` (line 18, 35)

```python
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_auth.db")
TEST_DB_URL = "sqlite:///./test_auth.db"
```

테스트 DB가 인메모리(`sqlite:///:memory:`)가 아닌 파일(`test_auth.db`)을 사용한다. `db_session` fixture가 rollback을 수행하지만, `test_migrations.py`가 `alembic upgrade/downgrade` CLI 명령을 **별도 프로세스**로 실행하므로 동일한 파일 DB에 직접 DDL을 커밋한다. 이로 인해 migration 테스트와 API 테스트가 동시 실행될 때 DB 파일 상태가 충돌할 수 있다.

**권장 수정**: conftest에서 `sqlite:///:memory:`를 사용하고, `test_migrations.py`에는 전용 임시 파일 경로(`tmp_path` fixture)를 사용한다.

---

### C-02. `test_models.py` — `scope="module"` 세션에서 직접 삭제·커밋으로 테스트 간 상태 누출

**파일**: `backend/tests/unit/test_models.py` (lines 110–111, 125–126, 159–160, 193–195, 208–210, etc.)

`db_session` fixture가 `scope="module"`로 선언되어 있어 **같은 세션 인스턴스가 모듈 내 모든 테스트에서 공유**된다. 각 테스트는 직접 `db_session.delete(user); db_session.commit()`로 정리를 시도하지만, 중간에 테스트가 실패하면 cleanup이 실행되지 않아 이후 테스트에 더미 데이터가 남는다.

특히 `test_user_email_unique_constraint_enforced` (line 128)는 `db_session.rollback()`을 직접 호출하는데, 이는 이후 테스트가 이미 더러운 상태의 세션을 사용하게 만들 수 있다.

**권장 수정**: `scope="function"`으로 변경하거나, 각 테스트 내부 cleanup을 `try/finally`로 감싼다.

---

### C-03. `routers/auth.py` — `UserRegisterRequest`에 Pydantic `EmailStr` 미적용

**파일**: `backend/src/app/routers/auth.py` (line 22)

```python
class UserRegisterRequest(BaseModel):
    email: str       # ← EmailStr이어야 함
    username: str
    password: str
```

`email` 필드가 `str` 타입이라 Pydantic 레벨에서 이메일 형식 검증이 이뤄지지 않는다. `admin@` 또는 `not-an-email` 같은 값이 DB에 저장될 수 있다. `UserLoginRequest` (line 28)도 동일하다. `pydantic[email]` 의존성은 이미 임포트 구문(`from pydantic import BaseModel, EmailStr`)에 있으나 실제로 사용되지 않는다.

**권장 수정**: `email: str` → `email: EmailStr`

---

### C-04. `auth.py` — `datetime.utcnow()` deprecated, naive datetime 사용

**파일**: `backend/src/app/auth.py` (lines 30, 32)
**파일**: `backend/src/models/user.py` (line 16, 17)
**파일**: `backend/src/models/defect.py` (line 20, 21)

```python
expire = datetime.utcnow() + expires_delta   # naive UTC datetime
```

Python 3.12+에서 `datetime.utcnow()`는 deprecated이며, timezone-aware datetime을 반환하지 않는다. JWT 라이브러리 (`python-jose`)가 내부적으로 timezone-aware datetime과 비교할 경우 비교 오류가 발생할 수 있다.

`test_auth_api.py`의 만료 토큰 테스트 (line 384)는 `datetime.now(tz=timezone.utc)`를 올바르게 사용하지만, **소스 코드가 naive datetime으로 토큰을 생성**하여 일관성이 없다.

**권장 수정**: `datetime.now(tz=timezone.utc)` 사용으로 통일.

---

### C-05. `Sidebar.test.tsx` — 잘못된 import 경로 (파일 불일치)

**파일**: `frontend/src/__tests__/Sidebar.test.tsx` (line 28)

```typescript
import Layout from '../components/Layout/Sidebar';
```

실제로 `Sidebar.tsx` 파일은 존재하지 않는다. 해당 컴포넌트는 `Layout.tsx`에 통합되어 있으며, 올바른 경로는 `../components/Layout/Layout` (또는 해당 파일명)이다. 테스트 파일 맨 위 주석(line 6)도 이 사실을 인정하고 있다. 이 import 오류는 **빌드 단계에서 즉시 실패**를 야기한다.

**권장 수정**: import 경로를 실제 Layout 파일 경로로 수정하거나, Sidebar를 별도 파일로 분리한다.

---

### C-06. `LoginPage.tsx` — `<label>` 과 `<input>` 연결 누락 (접근성 + 테스트 호환성)

**파일**: `frontend/src/pages/LoginPage.tsx` (lines 67–69, 88–90)

```tsx
<label className="...">
  Email address
</label>
<input type="email" ... />
```

`<label>`에 `htmlFor` 속성이 없고 `<input>`에 `id` 속성이 없다. `LoginPage.test.tsx`는 `screen.getByLabelText(/email address/i)` (line 95)를 사용해 요소를 찾는데, label-input 연결이 없으면 이 쿼리는 실패한다. `RegisterPage.tsx`도 동일한 문제를 가진다.

**권장 수정**: 각 `<label>`에 `htmlFor="email"` 추가, `<input>`에 `id="email"` 추가.

---

## 🟡 Warning (권장 수정)

### W-01. `conftest.py` — `register_and_login()` 헬퍼 함수가 login API가 아닌 register API만 호출

**파일**: `backend/tests/conftest.py` (lines 95–120)

함수 이름이 `register_and_login`이지만 실제로는 `POST /api/auth/register`만 호출하고 그 응답 토큰을 반환한다. 로그인 API(`POST /api/auth/login`)를 별도로 테스트하는 것이 C6 테스트에서만 이루어진다. 이름이 동작을 오해하게 만들며, 만약 register와 login이 별도로 분리될 경우 이 헬퍼는 잘못된 토큰을 반환할 수 있다.

**권장 수정**: 함수명을 `register_user_and_get_token()`으로 변경하거나, 실제로 login API도 호출하도록 확장.

---

### W-02. `test_auth_api.py` — `SECRET_KEY` 하드코딩 중복

**파일**: `backend/tests/integration/test_auth_api.py` (lines 23–24, 31)

```python
os.environ.setdefault("SECRET_KEY", "test-secret-key")
SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key")
```

`"test-secret-key"` 리터럴이 `conftest.py` (line 17)와 `test_auth_api.py` (lines 23, 31) 세 곳에 중복 존재한다. 키 변경 시 한 곳을 누락할 수 있다.

**권장 수정**: `conftest.py`에 상수로 정의하고 import하여 단일 소스로 관리.

---

### W-03. `test_migrations.py` — 테스트 순서 의존성 (module-scoped, 순서 의존)

**파일**: `backend/tests/integration/test_migrations.py` (lines 95–181)

`test_all_tables_exist`(line 104)는 `test_alembic_upgrade_head`(line 95)가 먼저 실행되어 테이블이 생성되어 있다고 가정한다. `test_alembic_downgrade_and_upgrade`(line 137) 역시 head 상태를 전제한다. pytest는 기본적으로 파일 순서대로 실행하지만, `--randomly` 플러그인이나 병렬 실행 시 순서가 뒤바뀔 수 있다.

각 테스트가 자체적으로 `alembic upgrade head`를 먼저 실행하고 있으나, 실패한 downgrade 후 재실행 시 상태가 불확실하다.

**권장 수정**: 각 테스트 시작 전 `downgrade base` 후 `upgrade head`를 실행하거나, 명시적 `@pytest.mark.dependency` 사용.

---

### W-04. `routers/auth.py` — `/login/form` 엔드포인트 테스트 누락

**파일**: `backend/src/app/routers/auth.py` (lines 139–169)

`POST /api/auth/login/form` 엔드포인트가 존재하지만 `test_auth_api.py`에 이 엔드포인트에 대한 테스트가 전혀 없다. OAuth2 form 로그인을 지원하는 엔드포인트인데, `is_active` 체크도 누락되어 있다 (line 150에서 `is_active` 검사 없이 토큰 발급).

**권장 수정**: `/login/form`에 대한 테스트 추가; 소스에 `is_active` 체크 추가.

---

### W-05. `authStore.test.ts` — zustand/persist와 localStorage의 이중 저장 검증 부재

**파일**: `frontend/src/__tests__/authStore.test.ts`

`authStore.ts`는 두 가지 방식으로 localStorage에 데이터를 저장한다:
1. `persist` 미들웨어 (key: `qa-auth-store`)
2. `login()` 내부의 직접 `localStorage.setItem('access_token', token)` 호출

테스트는 `'access_token'` 키만 검증하고(lines 67–71), `zustand/persist`가 `'qa-auth-store'` 키에 저장하는 내용은 검증하지 않는다. 또한 `persist` 미들웨어가 초기 로드 시 localStorage에서 상태를 복원하는 시나리오(hydration)가 테스트되지 않는다.

---

### W-06. `RegisterPage.test.tsx` — 비밀번호 불일치 시나리오 테스트 누락

**파일**: `frontend/src/__tests__/RegisterPage.test.tsx`

`RegisterPage.tsx`의 `validate()` 함수(line 41)는 비밀번호와 확인 비밀번호가 다를 경우 `'Passwords do not match'` 오류를 표시하지만, 이에 대한 테스트가 없다. 또한 username이 3자 미만일 경우의 에러(`'Username must be at least 3 characters'`)도 테스트되지 않았다.

---

### W-07. `LoginPage.test.tsx` — API 성공/실패 플로우 테스트 부재

**파일**: `frontend/src/__tests__/LoginPage.test.tsx`

현재 테스트는 폼 렌더링과 클라이언트 사이드 validation만 검증한다. 다음 시나리오가 누락되어 있다:
- 올바른 credentials 입력 → API 성공 → navigate 호출 확인
- API 실패(401) → toast.error 호출 확인
- 로딩 상태에서 버튼 disabled 확인

`authService.login`을 이미 mock하고 있으므로 이 테스트들을 추가하는 것이 어렵지 않다.

---

### W-08. `user.py` — `updated_at` 컬럼이 테스트에서 검증되지 않음

**파일**: `backend/src/models/user.py` (line 17)
**파일**: `backend/tests/unit/test_models.py` `TestUserModel`

`updated_at` 컬럼이 User 모델에 존재하지만 `test_user_table_columns`(line 75)의 `required` 집합에 포함되지 않는다. Defect 모델의 `updated_at`(defect.py line 21)도 동일하다.

---

### W-09. `routers/auth.py` — `TokenResponse.user` 필드가 `dict` 타입 (타입 안전성 부재)

**파일**: `backend/src/app/routers/auth.py` (line 35)

```python
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict     # ← 타입이 너무 느슨함
```

`user` 필드가 `dict`로 정의되어 Pydantic이 응답 스키마 유효성을 강제하지 못한다. 이미 정의된 `UserResponse` 모델을 재사용하면 OpenAPI 문서 자동 생성과 런타임 유효성이 모두 개선된다.

**권장 수정**: `user: dict` → `user: UserResponse`

---

### W-10. `Sidebar.test.tsx` — `data-testid="sidebar"` attribute 누락을 테스트 내부 주석으로만 처리

**파일**: `frontend/src/__tests__/Sidebar.test.tsx` (lines 84–94)
**파일**: `frontend/src/components/Layout/Sidebar.tsx` (line 48)

테스트는 `data-testid="sidebar"`가 `<aside>` 요소에 없음을 인지하고 role fallback을 사용한다. 그러나 이 attribute 추가는 실제 소스 파일에 반영되지 않았다. TDD 계획의 DoD 요건을 충족하려면 `<aside>` 태그에 `data-testid="sidebar"`를 추가해야 한다.

---

## 🟢 Approved (잘 된 부분)

### A-01. 보안: 응답에 `hashed_password` 노출 방지 테스트가 철저함

`test_auth_api.py`는 register (line 63–78), login (line 313–330), /me (line 358–372) 세 엔드포인트 모두에 대해 `hashed_password`가 응답에 포함되지 않는다는 것을 명시적으로 검증한다. 실제 구현(`UserResponse` 모델)도 이를 올바르게 배제하고 있다.

### A-02. JWT 보안 테스트 포괄적 커버리지

`TestMeEndpoint` 클래스(test_auth_api.py lines 337–432)는 유효한 토큰, 만료된 토큰, 잘못된 서명 키, 완전히 비정형 토큰 등 모든 JWT 실패 경로를 다루며, 각각 HTTP 401을 올바르게 검증한다.

### A-03. `get_current_user()`의 비활성 사용자 처리

**파일**: `backend/src/app/auth.py` (lines 70–75)

비활성 계정(`is_active=False`)에 대해 403을 반환하는 로직이 존재하고, login 엔드포인트(routers/auth.py line 115–119)도 이를 처리한다.

### A-04. `conftest.py` — `db_session` fixture의 rollback 격리 패턴

각 테스트 후 DB 트랜잭션을 rollback하여 통합 테스트 간 격리를 보장하는 패턴은 올바르게 구현되어 있다(lines 56–64). `app.dependency_overrides`를 사용한 `get_db` 교체 방식도 FastAPI 모범 사례에 부합한다.

### A-05. `ProtectedRoute.test.tsx` — location state 전달 검증

단순한 리다이렉트 확인을 넘어 `state={{ from: location }}`이 올바르게 전달되어 로그인 후 원래 페이지로 복귀할 수 있는지도 검증한다(lines 84–91). `LocationDisplay` 헬퍼 컴포넌트의 활용이 깔끔하다.

### A-06. `test_models.py` — schema 검증과 동작 검증의 분리

inspector를 이용한 schema 검증(컬럼 존재, PK, FK, unique 제약)과 실제 DB 인서트를 이용한 default 값 검증을 별도 테스트로 명확히 분리한 구조가 훌륭하다.

### A-07. 패스워드 해싱 검증 (DB 직접 조회)

`test_register_password_is_hashed` (test_auth_api.py lines 80–102)는 API 응답뿐 아니라 DB에 실제 저장된 값을 직접 조회해서 bcrypt 해시인지 확인한다. 이는 진정한 통합 테스트의 모범 사례다.

### A-08. `RegisterPage` — 비밀번호 강도 지표 구현 완성도

`RegisterPage.tsx`의 `passwordStrength()` 함수(lines 72–81)와 강도 레이블 표시 로직(lines 83–85, 172–174)이 명확하고, `RegisterPage.test.tsx`는 0~4단계 모든 강도 레벨을 테스트한다.

---

## 파일별 상세 리뷰

### `backend/tests/conftest.py`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 18, 35 | 🔴 Critical | 파일 기반 SQLite 사용. 마이그레이션 테스트와 충돌 가능. `sqlite:///:memory:` 권장 |
| 17 | 🟡 Warning | `"test-secret-key"` 리터럴이 여러 파일에 중복 — 상수화 필요 |
| 95 | 🟡 Warning | `register_and_login` 함수명이 동작을 오해하게 함 — register만 수행 |
| 77–81 | 🟢 Good | `override_get_db`에서 `finally: pass` 처리로 세션 rollback을 fixture에 위임하는 패턴 정확 |

---

### `backend/tests/unit/test_models.py`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 33–39 | 🔴 Critical | `scope="module"` db_session — 테스트 간 상태 공유로 오염 위험 |
| 128–145 | 🔴 Critical | 테스트 내부에서 직접 `rollback()` 호출 — session scope 오염 |
| 75 | 🟡 Warning | `updated_at` 컬럼이 required 집합에서 누락 |
| 24–30 | 🟢 Good | `scope="module"` engine fixture로 테이블 생성 1회만 수행 — 효율적 |
| 52–63 | 🟢 Good | `column_names`, `get_column` 헬퍼 함수로 중복 제거 |

---

### `backend/tests/integration/test_auth_api.py`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 31 | 🟡 Warning | `SECRET_KEY` 하드코딩 중복 |
| 251–286 | 🟢 Good | JWT 만료 시간 검증이 before/after 타임스탬프를 활용한 범위 검사로 정확 |
| 379–406 | 🟢 Good | 만료 토큰, 잘못된 서명, 비정형 토큰 3가지 모두 401 검증 |
| — | 🟡 Warning | 비활성 사용자로 로그인 시도하는 테스트 없음 (login 엔드포인트의 403 분기 미검증) |

---

### `backend/tests/integration/test_migrations.py`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 104–114 | 🟡 Warning | `test_all_tables_exist`가 이전 테스트 실행 상태에 암묵적으로 의존 |
| 56–79 | 🟢 Good | `run_alembic()` 헬퍼가 `PYTHONPATH` 설정, 환경변수 전파를 올바르게 처리 |
| 36–37 | 🟡 Warning | `DATABASE_URL` fallback이 `"sqlite:///./test.db"` — conftest의 `test_auth.db`와 다른 파일 사용. CI에서 혼선 가능 |

---

### `backend/src/models/user.py`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 16–17 | 🔴 Critical | `datetime.utcnow()` deprecated; timezone-naive datetime 사용 |
| 11–12 | 🟢 Good | `email`과 `username` 모두 `unique=True, index=True, nullable=False` 올바르게 설정 |
| 20–21 | 🟡 Warning | `lazy="dynamic"` relationship은 SQLAlchemy 2.0에서 deprecated (`select` 또는 `lazy="dynamic"` → `lazy="dynamic_sync"` 고려) |

---

### `backend/src/models/defect.py`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 13 | 🟡 Warning | `severity` 컬럼이 `nullable=False`인데 `status` (line 15)는 `nullable` 지정 없음 — 의도 불명확 |
| 16 | 🟡 Warning | `reporter` (String) 컬럼과 `reporter_id` (FK) 컬럼이 중복 존재 — reporter 정보를 두 가지 방식으로 저장하는 것은 데이터 불일치 위험 |
| 19 | 🟢 Good | `embedding` 컬럼을 JSON 배열로 저장하는 것은 벡터 DB 도입 전 임시 구현으로 타당 |

---

### `backend/src/app/auth.py`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 30, 32 | 🔴 Critical | `datetime.utcnow()` deprecated — `datetime.now(tz=timezone.utc)` 사용 필요 |
| 63–64 | 🟡 Warning | `user_id: Optional[int] = payload.get("sub")` — sub는 `str`로 인코딩되었으므로 `int(user_id)` 변환은 line 67에서 처리되나, 타입 힌트가 `Optional[str]`이어야 함 |
| 80–90 | 🟡 Warning | `get_current_user_optional`은 `OAuth2PasswordBearer`를 의존성으로 사용하는데, 이 scheme은 토큰이 없으면 자동으로 401을 반환한다. `optional` 동작을 위해서는 `auto_error=False`인 별도 scheme이 필요 |
| 16–18 | 🟢 Good | `verify_password`와 `get_password_hash` 분리 — 단일 책임 원칙 준수 |

---

### `backend/src/app/routers/auth.py`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 22, 28 | 🔴 Critical | `email: str` → `email: EmailStr` 변경 필요 |
| 35 | 🟡 Warning | `user: dict` → `user: UserResponse`로 타입 강화 권장 |
| 139–169 | 🟡 Warning | `/login/form` 엔드포인트의 `is_active` 체크 누락 (line 150) |
| 67–71 | 🟢 Good | 비밀번호 길이 검증이 Pydantic validator 대신 라우터에서 처리 — 400 반환으로 테스트와 일치 |
| 53–64 | 🟢 Good | 이메일 중복, 사용자명 중복 각각 별도로 체크하여 명확한 에러 메시지 제공 |

---

### `frontend/src/__tests__/authStore.test.ts`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 16–21 | 🟢 Good | `resetStore()`로 각 테스트 전 Zustand 상태 초기화 — 테스트 독립성 확보 |
| — | 🟡 Warning | `zustand/persist` hydration 시나리오 (localStorage에서 상태 복원) 테스트 없음 |
| 108–117 | 🟡 Warning | logout의 `'user'` key 제거 테스트가 수동으로 key를 설정한 후 확인하는 방식 — persist 미들웨어가 이 key를 자동 관리하지 않음을 보여주는 설계 불일치 |

---

### `frontend/src/__tests__/ProtectedRoute.test.tsx`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 61–92 | 🟢 Good | 3개 테스트 모두 독립적이며, `beforeEach`에서 mock 초기화 — 모범 사례 |
| — | 🟡 Warning | `isLoading` 상태에서의 ProtectedRoute 동작 (토큰 갱신 중) 시나리오 미검증 |

---

### `frontend/src/__tests__/LoginPage.test.tsx`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 82–84 | 🟡 Warning | 주석으로 `data-testid` 추가를 요청하지만 실제 소스에 반영 안됨 — Green phase 진입 전 추가 필요 |
| — | 🟡 Warning | 성공적인 로그인 → navigate 호출 테스트 없음 |
| — | 🟡 Warning | API 오류 → toast.error 호출 테스트 없음 |
| 100–137 | 🟢 Good | 빈 이메일, 잘못된 형식, 빈 비밀번호 — 세 가지 validation 경로 모두 커버 |

---

### `frontend/src/__tests__/RegisterPage.test.tsx`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 1–7 | 🟢 Good | 파일 상단 주석에서 TDD 계획(한국어 레이블)과 실제 구현(영어 레이블) 간 불일치를 명시적으로 문서화 — 정직한 문서화 |
| — | 🟡 Warning | 비밀번호 불일치 validation 테스트 없음 |
| — | 🟡 Warning | username 3자 미만 validation 테스트 없음 |
| — | 🟡 Warning | confirmPassword 필드 비어있을 때 테스트 없음 |
| 191–218 | 🟢 Good | `authService.register` mock 사용 + 실제 navigate 결과(/dashboard 도달) 검증 |

---

### `frontend/src/__tests__/Sidebar.test.tsx`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 28 | 🔴 Critical | `import Layout from '../components/Layout/Sidebar'` — Sidebar.tsx 파일 미존재. 빌드 즉시 실패 |
| 84–94 | 🟡 Warning | `data-testid="sidebar"` fallback 로직이 test에 있지만 실제 소스에는 미추가 |
| 121–130 | 🟢 Good | NavLink의 active class를 직접 className으로 검증 — 구현 세부사항을 적절히 테스트 |
| 46–55 | 🟢 Good | lucide-react icon들을 `() => null`로 모킹하여 SVG 관련 테스트 노이즈 제거 |

---

### `frontend/src/store/authStore.ts`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 22 | 🟡 Warning | `localStorage.setItem('access_token', token)` 직접 호출이 `persist` 미들웨어의 저장 외에 추가로 수행됨 — 동일 데이터가 `qa-auth-store`와 `access_token` 두 키에 이중 저장됨 |
| 27–29 | 🟢 Good | logout에서 `access_token`과 `user` 두 키 모두 제거 |
| 36–43 | 🟡 Warning | `partialize`로 `token`, `user`, `isAuthenticated`만 persist — `updateUser` action은 persist 후 동기화가 불완전할 수 있음 |

---

### `frontend/src/components/Layout/ProtectedRoute.tsx`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 13–15 | 🟢 Good | `state={{ from: location }}`으로 원래 경로 보존 — 로그인 후 복귀 기능 |
| — | 🟡 Warning | `isAuthenticated` 외에 `token` 유효성(만료 여부)을 클라이언트에서 추가 검증하지 않음. 만료된 토큰이 localStorage에 남아 있으면 `isAuthenticated=true`로 잘못 인식될 수 있음 |

---

### `frontend/src/pages/LoginPage.tsx`

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 67–69, 88–90 | 🔴 Critical | `<label>`에 `htmlFor` 누락, `<input>`에 `id` 누락 — `getByLabelText` 테스트 실패 원인 |
| 21–27 | 🟢 Good | 이메일 정규식 + 빈 값 체크를 명확하게 분리 |
| 40–47 | 🟢 Good | API 에러를 `err?.response?.data?.detail`에서 추출하는 방어적 코딩 |

---

### `frontend/src/components/Layout/Sidebar.tsx` (실제 파일명: `Layout.tsx` 기능 포함)

| 라인 | 심각도 | 내용 |
|------|--------|------|
| 48 | 🟡 Warning | `<aside>` 태그에 `data-testid="sidebar"` 누락 |
| 14–33 | 🟢 Good | `navItems` 배열로 nav 링크 선언, 코드 중복 없음 |
| 64–89 | 🟢 Good | NavLink의 `className` prop에 함수를 사용하여 active 상태 스타일 적용 — React Router 모범 사례 |

---

## TDD 원칙 준수 평가

### Red 단계 역할 분석

TDD 계획(`sprint1-tdd-plan.md`)의 Red 단계 테스트 코드와 실제 제출된 테스트 파일을 비교하면:

1. **C1 (User 모델)**: TDD 계획의 Red 단계는 `"name"`, `"role"` 컬럼을 검증하지만 실제 구현은 `"username"`, `"is_active"`, `"is_admin"`을 사용한다. 테스트가 소스보다 먼저 작성되었다면 이 불일치가 수정되었을 것이나, **실제 구현에 맞게 테스트가 사후에 수정**된 것으로 보인다.

2. **C10 (RegisterPage)**: 테스트 파일 상단 주석이 명시적으로 "TDD 계획은 한국어 레이블을 지정했지만 실제 구현은 영어를 사용한다"고 밝히고 있다. 이는 테스트가 구현을 주도하지 않고 **구현에 맞게 테스트가 작성**되었음을 방증한다.

3. **`data-testid` 속성 누락**: 여러 테스트 파일이 주석으로 "이 속성을 소스에 추가해야 한다"고 명시하는데, 실제로 소스에 추가되지 않았다. TDD라면 테스트가 먼저 Red를 만들어야 하므로 이 속성이 소스에 없는 것이 정상이나, **테스트 자체가 fallback 로직을 포함**하여 속성 없이도 통과하도록 작성된 점이 Red-Green 사이클의 엄격함을 약화시킨다.

---

## Green Phase 진입 전 필수 수정 사항

다음 항목들은 Green Phase(구현 완성) 시작 전에 반드시 해결해야 한다.

### 즉시 수정 (테스트 실행 차단)

- [ ] **[C-05]** `Sidebar.test.tsx` line 28: `import Layout from '../components/Layout/Sidebar'` → 올바른 파일 경로로 수정 (빌드 실패)
- [ ] **[C-06]** `LoginPage.tsx` lines 67–69, 88–90: `<label htmlFor="email">`, `<input id="email">` 추가 — `getByLabelText` 쿼리 실패 해결

### 보안 수정 (프로덕션 배포 전 필수)

- [ ] **[C-03]** `routers/auth.py` lines 22, 28: `email: str` → `email: EmailStr` (이메일 형식 서버 측 검증)
- [ ] **[C-04]** `auth.py` lines 30, 32 및 모든 모델 파일: `datetime.utcnow()` → `datetime.now(tz=timezone.utc)` (timezone-aware datetime)
- [ ] **[W-04]** `routers/auth.py` line 150: `/login/form` 엔드포인트에 `is_active` 체크 추가

### 테스트 신뢰성 수정

- [ ] **[C-01]** `conftest.py` lines 18, 35: 파일 기반 SQLite → `sqlite:///:memory:` 또는 테스트별 임시 파일로 변경
- [ ] **[C-02]** `test_models.py` lines 33–39: `db_session` fixture `scope="module"` → `scope="function"` 으로 변경
- [ ] **[W-10]** `Sidebar.tsx` (Layout.tsx) line 48: `<aside>` 태그에 `data-testid="sidebar"` 추가

### 커버리지 보완 (Sprint 1 DoD 충족)

- [ ] **[W-06]** `RegisterPage.test.tsx`: 비밀번호 불일치, username 길이 부족 validation 테스트 추가
- [ ] **[W-07]** `LoginPage.test.tsx`: 성공적인 로그인 후 navigate 호출, API 실패 후 toast.error 테스트 추가
- [ ] **[W-04]** `test_auth_api.py`: 비활성 계정으로 로그인 시도 → 403 반환 테스트 추가
- [ ] **[W-04]** `test_auth_api.py`: `/login/form` 엔드포인트 테스트 추가
