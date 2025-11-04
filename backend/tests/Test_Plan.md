# 🧪 Test Plan — Quill_N_Code Backend

**Goal:**  
Ensure production stability, data integrity, and regression safety through layered automated testing.  
Covers **unit**, **integration**, and **end-to-end (E2E)** tests for all major services.

---

## 📂 Test Layers

| Layer | Scope | DB | External Services | Purpose |
|-------|-------|----|------------------|----------|
| Unit | Single functions/modules | ❌ Mocked | Mocked | Validate logic, permissions, validation rules |
| Integration | Service boundaries (DB, ORM) | ✅ Real (transactional) | Dummy/Mimicked | Validate data persistence and relationships |
| E2E | Full HTTP API | ✅ Real | ✅ Dummy/Mock | Validate user journeys and API contracts |

---

## 🧱 Core Infrastructure

- **Database fixture:** per-test transaction with savepoint (`db_session`).
- **Factories:** create valid related data with minimal setup.
- **External dummies:**
  - `DummyMailer` → captures sent emails
  - `DummyCloudinary` → returns deterministic URLs
- **Seeding:** Roles `user`, `creator`, `moderator`, `superadmin` are reusable and idempotent.
- **Markers:**  
  `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.security`, `@pytest.mark.performance`

---

## ⚙️ Services Coverage

### 1. Auth Service
**Unit Tests**
- [ ] Password hashing/verification works for valid & invalid inputs  
- [ ] JWT token creation & decode (exp, iat, claims)  
- [ ] Error handling: invalid credentials → 401, disabled user → 403  
- [ ] Rate limiting (if implemented)

**Integration Tests**
- [ ] Login/Signup flow writes correct DB rows  
- [ ] Refresh token rotation, blacklist, expiry  
- [ ] Disabled/deleted user cannot authenticate  
- [ ] Correct user roles assigned on signup  

**E2E**
- [ ] Sign-up → email verification (mock mailer) → login → access → logout  
- [ ] Tampered/expired tokens rejected  
- [ ] Unauthorized routes blocked (403/401)

---

### 2. Story Service
**Unit**
- [ ] Only `creator` or above can create  
- [ ] Only author can update  
- [ ] Only `superadmin` can delete  
- [ ] State transitions: `draft → published → rejected` correct  
- [ ] Field validation (title/content lengths, sanitization)

**Integration**
- [ ] Create story persists correctly (timestamps, foreign keys)  
- [ ] Update modifies fields, preserves ownership  
- [ ] Delete = soft delete (`deleted_at` set)  
- [ ] Cascade/soft delete of comments/likes validated  
- [ ] Pagination & ordering correct  
- [ ] Concurrency: two updates handled predictably

**E2E**
- [ ] Full CRUD via API (with auth tokens)  
- [ ] Creator can publish; reader cannot edit  
- [ ] Tag/filter queries return correct results  

---

### 3. Comments Service
**Unit**
- [ ] Auth required  
- [ ] Max length, content sanitization enforced  
- [ ] Ownership: only author/moderator can edit/delete  

**Integration**
- [ ] Add comment persists with valid story/user  
- [ ] Delete handles parent/child relations (if threaded)  
- [ ] Pagination consistent ordering  

**E2E**
- [ ] Comment create/edit/delete via API  
- [ ] Unauthorized actions rejected  

---

### 4. Interactions (Likes / Bookmarks)
**Unit**
- [ ] Idempotent toggle (like/unlike, bookmark/unbookmark)  
- [ ] Counts increment/decrement correctly  

**Integration**
- [ ] Likes stored only once per user/story  
- [ ] Concurrency (parallel toggles) safe under unique constraint  
- [ ] Bookmarks returned correctly in user profile  

**E2E**
- [ ] Like/unlike via UI → count updates live  

---

### 5. Moderation / Flags
**Unit**
- [ ] `flag_story` / `flag_comment` sets reporter & reason  
- [ ] `approve_story` → story published, open flags closed  
- [ ] `reject_story` → story rejected, flags updated  
- [ ] Role guard: only `moderator`+ can approve/reject  
- [ ] `moderate_content()` flags profanity accurately  

**Integration**
- [ ] Flag persists correct `flagged_by_user_id`, `story_id`/`comment_id`  
- [ ] Approve/reject commits both story & flags atomically  
- [ ] Multiple flags resolved together  
- [ ] Rollback safety: failure leaves data consistent  

**E2E**
- [ ] User flags story → moderator sees → approve → author notified  
- [ ] Rejected story hidden from readers  

---

### 6. Notifications
**Unit**
- [ ] Message formatting correct for each event type  
- [ ] Delivery type (email, in-app) logic validated  

**Integration**
- [ ] Approve/reject triggers notifications  
- [ ] Mark-as-read updates DB  
- [ ] Pagination and unread counts accurate  
- [ ] Notify failure doesn’t break main transaction (if best-effort)

**E2E**
- [ ] Notification visible in UI after story approval  

---

### 7. Tags / Media / Admin / Analytics / System
**Unit**
- [ ] Tag slug creation & dedupe  
- [ ] Media URL building & file validation  
- [ ] Admin permission checks  
- [ ] Analytics functions compute correct aggregates  

**Integration**
- [ ] Tag assignment stored, searchable  
- [ ] Media upload uses dummy cloud service  
- [ ] Admin routes restricted by role  
- [ ] Analytics endpoints return expected values  

**E2E**
- [ ] Tag filter API returns expected stories  
- [ ] Media upload → URL accessible (dummy URL)  
- [ ] Admin bulk operations succeed  

---

## 🔒 Security & Resilience Tests

**Security**
- [ ] Auth bypass attempts return 403  
- [ ] SQL injection, XSS, SSRF attempts sanitized  
- [ ] Password hashes never exposed  
- [ ] Rate limits enforced  

**Resilience**
- [ ] DB connection loss handled gracefully  
- [ ] External service failures (mailer, cloud) → proper fallback  
- [ ] Background tasks retried or queued correctly  

**Performance**
- [ ] P95 latency under SLA (target: < 200ms for reads)  
- [ ] Query count per request bounded (no N+1)  
- [ ] Index coverage validated  

---

## ⚙️ Migration Tests

- [ ] Fresh migration on empty DB succeeds  
- [ ] Downgrade back to base works cleanly  
- [ ] Data preserved after column additions/renames  

---

## 🌐 API Contract Tests

- [ ] OpenAPI schema snapshot matches previous version  
- [ ] Response field names/types consistent  
- [ ] Enum/string constants not renamed silently  

---

## 🧪 Repo Layout (Recommended)

        tests/
        unit/
        services/
        test_auth_service.py
        test_story_service.py
        test_comments_service.py
        test_interactions_service.py
        test_moderation_service.py
        test_notifications_service.py
        test_tags_service.py
        test_media_service.py
        integration/
        test_db_migrations.py
        test_story_crud_integration.py
        test_moderation_integration.py
        test_notifications_integration.py
        test_tags_media_integration.py
        e2e/
        test_auth_flow_e2e.py
        test_creator_journey_e2e.py
        test_moderator_journey_e2e.py
        test_reader_journey_e2e.py
        security/
        test_authz_enforcement.py
        test_input_sanitization.py
        performance/
        test_query_counts.py
        test_simple_load_smoke.py



---

## ✅ CI/CD Quality Gates

| Stage | Check | Target |
|-------|--------|---------|
| **Pre-commit** | lint (ruff/flake8), type check (mypy) | 0 errors |
| **Unit tests** | `pytest -m unit` | ≥95% pass, <1s/test avg |
| **Integration tests** | `pytest -m integration` | ≥90% pass |
| **Coverage** | line coverage | ≥80% total, ≥90% critical modules |
| **Security** | bandit + pip-audit | 0 high severity |
| **E2E (staging)** | Smoke suite via GitHub Actions/Docker | 100% pass before deploy |

---

## 🧩 Future Additions

- [ ] Property-based tests (Hypothesis) for text moderation & slugify  
- [ ] Contract tests shared with frontend (JSON shape)  
- [ ] Canary smoke tests post-deploy (login, story list)  
- [ ] Load testing (Locust) for top endpoints  
- [ ] Chaos testing (DB/mailer failure simulations)

---

## 🏁 Definition of Done (for Testing)

A feature is **test-ready** when:
1. It has ≥1 unit test per logical branch.  
2. All DB mutations verified in integration tests.  
3. Permission/role behavior validated.  
4. API path covered by at least one E2E flow.  
5. No regression detected in existing test suites.  
6. Coverage report doesn’t regress baseline threshold.  

---