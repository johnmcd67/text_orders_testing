# Office 365 Login Implementation Plan - Text Orders App

## Status: READY TO IMPLEMENT

**Last Updated:** 2025-11-20

---

## 🎯 OVERVIEW

This document outlines the implementation plan for adding Office 365 authentication to the Text Orders web application. The implementation follows the proven architecture already deployed in the sister PDF Orders app.

**Key Differences from PDF Orders:**
- Frontend uses Vite (not CRA), so environment variables use `VITE_*` prefix instead of `REACT_APP_*`
- All other architecture and flow remains identical

---

## ✅ PRE-IMPLEMENTATION CHECKLIST

### Already Completed:
- [x] Azure App Registration created (`AZURE_CLIENT_ID` configured)
- [x] Azure Tenant ID obtained (`AZURE_TENANT_ID` configured)
- [x] Frontend environment variables set in `frontend/.env`
  - `VITE_AZURE_CLIENT_ID=f8da0754-9da4-4537-a70e-e96912105bf1`
  - `VITE_AZURE_TENANT_ID=200ec09f-c5a4-4f85-aea3-d11aa273449c`
  - `VITE_API_URL=http://localhost:8000/api`
- [x] Backend environment variables partially set in `.env`
  - `AZURE_CLIENT_ID=f8da0754-9da4-4537-a70e-e96912105bf1`
  - `AZURE_TENANT_ID=200ec09f-c5a4-4f85-aea3-d11aa273449c`

### Pending:
- [ ] Generate and set `JWT_SECRET` in backend `.env`
- [ ] Verify Azure App Registration platform type is "Single-Page Application (SPA)"
- [ ] Verify redirect URIs configured: `http://localhost:5173` and `http://localhost:5173/login`
- [ ] Verify API permissions granted (User.Read, profile, email, openid)

---

## 🚨 CRITICAL: Azure App Registration Requirements

### Application Type MUST Be "Single-Page Application (SPA)"

**Why this matters:**
- Frontend uses `@azure/msal-browser` which requires SPA configuration
- If configured as "Web" application, you will get error: `AADSTS9002326: Cross-origin token redemption is permitted only for the 'Single-Page Application' client-type`

**How to verify:**
1. Go to [Azure Portal](https://portal.azure.com) → Azure Active Directory → App registrations
2. Find your app registration (Client ID: `f8da0754-9da4-4537-a70e-e96912105bf1`)
3. Go to **Authentication** section
4. Under **Platform configurations**, verify:
   - Platform type is **"Single-page application"** (NOT "Web")
   - Redirect URIs include:
     - `http://localhost:5173`
     - `http://localhost:5173/login`
   - Implicit grant is NOT checked (not needed for SPA)

**Required API Permissions:**
1. Go to **API permissions** section
2. Verify these Microsoft Graph delegated permissions are granted:
   - `User.Read` - Read user profile
   - `profile` - View users' basic profile
   - `email` - View users' email address
   - `openid` - Sign users in
3. Ensure "Grant admin consent" is clicked

---

## 🔐 ENVIRONMENT VARIABLES

### Backend `.env` (Root Directory)

**Current Status:**
```env
AZURE_TENANT_ID=200ec09f-c5a4-4f85-aea3-d11aa273449c  # ✅ Set
AZURE_CLIENT_ID=f8da0754-9da4-4537-a70e-e96912105bf1  # ✅ Set
JWT_SECRET=                                            # ❌ NEEDS TO BE SET
```

**Action Required:**
Generate a secure JWT secret and add to `.env`:
```bash
# Generate using openssl (recommended)
openssl rand -base64 48

# Or generate online at: https://www.random.org/strings/
# Use length 64, alphanumeric + special characters
```

**Example:**
```env
JWT_SECRET=your_generated_secure_random_string_minimum_32_characters_longer_is_better
```

**Optional (for token expiration):**
```env
JWT_EXPIRES_IN=24h  # Default is 24 hours
```

### Frontend `frontend/.env`

**Current Status:**
```env
VITE_AZURE_CLIENT_ID=f8da0754-9da4-4537-a70e-e96912105bf1  # ✅ Set
VITE_AZURE_TENANT_ID=200ec09f-c5a4-4f85-aea3-d11aa273449c  # ✅ Set
VITE_API_URL=http://localhost:8000/api                     # ✅ Set
```

**No action required** - all frontend environment variables are correctly configured.

**Note:** Vite uses `VITE_*` prefix (not `REACT_APP_*` like Create React App).

---

## 📦 IMPLEMENTATION ROADMAP

The implementation is divided into 5 phases. All code can be copied/adapted from the PDF Orders app.

### Phase 1: Database Schema Setup

**Reference:** PDF Orders database schema

#### Task 1.1: Create Users Table

**SQL Schema:**
```sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    given_name VARCHAR(255),
    surname VARCHAR(255),
    microsoft_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_microsoft_id ON users(microsoft_id);
```

**Implementation:**
- [ ] Create SQL migration script in `postgres_schema/` directory
- [ ] Run migration against PostgreSQL database
- [ ] Verify table creation with `\dt users` in psql

**Verification:**
```bash
# Connect to database and verify
psql $DATABASE_URL -c "SELECT * FROM users LIMIT 5;"
```

---

### Phase 2: Backend Dependencies

#### Task 2.1: Update requirements.txt

**Add these dependencies:**
```txt
# JWT Authentication
python-jose[cryptography]>=3.3.0

# Password hashing (for future use)
passlib[bcrypt]>=1.7.4
```

**Implementation:**
- [ ] Update `requirements.txt`
- [ ] Run `pip install -r requirements.txt`
- [ ] Verify installation: `pip list | grep -E "(jose|passlib)"`

**Reference:** `C:\Users\AI_USER\Desktop\Scripts\OrderIntake_web_app\pdf_orders\requirements.txt`

---

### Phase 3: Backend Implementation

All files can be copied from PDF Orders app with minimal modifications.

#### Task 3.1: Create Backend Directory Structure

**Create these directories:**
```bash
mkdir -p backend/middleware
mkdir -p backend/services
mkdir -p backend/routes
```

**Verification:**
- [ ] `backend/middleware/` exists
- [ ] `backend/services/` exists
- [ ] `backend/routes/` exists

---

#### Task 3.2: Copy Authentication Utilities

**Source:** `pdf_orders/backend/utils/auth.py`
**Destination:** `backend/utils/auth.py`

**Purpose:**
- JWT token generation
- JWT token verification
- Token payload creation

**Key Functions:**
- `generate_token(payload: dict) -> str`
- `verify_token(token: str) -> dict`
- `create_user_payload(user: dict) -> dict`

**Implementation:**
- [ ] Copy file from PDF Orders
- [ ] Verify `JWT_SECRET` is loaded from environment
- [ ] No modifications needed (100% compatible)

**Reference:** [pdf_orders/backend/utils/auth.py](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/backend/utils/auth.py)

---

#### Task 3.3: Create Microsoft Auth Middleware

**Source:** `pdf_orders/backend/middleware/microsoft_auth.py`
**Destination:** `backend/middleware/microsoft_auth.py`

**Purpose:**
- Verify Microsoft access token with Microsoft Graph API
- Extract user profile from Graph API response
- Validate account data

**Key Functions:**
- `verify_microsoft_token_dependency(request: Request) -> dict`
- `validate_microsoft_account(account: dict) -> dict`

**Implementation:**
- [ ] Create `backend/middleware/__init__.py` (empty file)
- [ ] Copy `microsoft_auth.py` from PDF Orders
- [ ] No modifications needed

**Reference:** [pdf_orders/backend/middleware/microsoft_auth.py](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/backend/middleware/microsoft_auth.py)

---

#### Task 3.4: Create JWT Auth Middleware

**Source:** `pdf_orders/backend/middleware/auth.py`
**Destination:** `backend/middleware/auth.py`

**Purpose:**
- FastAPI dependency for protected routes
- Extract JWT token from Authorization header
- Verify token and return current user

**Key Functions:**
- `get_current_user(authorization: str = Header(None)) -> dict`

**Implementation:**
- [ ] Copy `auth.py` from PDF Orders
- [ ] No modifications needed

**Reference:** [pdf_orders/backend/middleware/auth.py](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/backend/middleware/auth.py)

---

#### Task 3.5: Create User Service

**Source:** `pdf_orders/backend/services/user_service.py`
**Destination:** `backend/services/user_service.py`

**Purpose:**
- Authenticate or create user from Microsoft profile
- User database operations (lookup, create, update)

**Key Functions:**
- `authenticate_microsoft_user(microsoft_user: dict) -> dict`
- `get_user_by_email(email: str) -> dict | None`
- `create_user_from_microsoft(microsoft_user: dict) -> dict`
- `create_user_payload(user: dict) -> dict`

**Implementation:**
- [ ] Create `backend/services/__init__.py` (empty file)
- [ ] Copy `user_service.py` from PDF Orders
- [ ] **IMPORTANT:** Update database connection imports if needed
  - PDF Orders may use `DatabaseHelper` differently
  - Verify compatibility with `backend/database.py` in Text Orders

**Reference:** [pdf_orders/backend/services/user_service.py](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/backend/services/user_service.py)

---

#### Task 3.6: Create Auth Routes

**Source:** `pdf_orders/backend/routes/auth.py`
**Destination:** `backend/routes/auth.py`

**Purpose:**
- Auth API endpoints for frontend to call

**Endpoints:**
- `POST /api/auth/microsoft` - Authenticate with Microsoft token, return JWT
- `GET /api/auth/profile` - Get current user profile (protected)
- `POST /api/auth/refresh` - Refresh JWT token (protected)
- `GET /api/auth/verify` - Verify token validity (protected)

**Implementation:**
- [ ] Create `backend/routes/__init__.py` (empty file)
- [ ] Copy `auth.py` from PDF Orders
- [ ] No modifications needed

**Reference:** [pdf_orders/backend/routes/auth.py](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/backend/routes/auth.py)

---

#### Task 3.7: Register Auth Routes in main.py

**File:** `backend/main.py`

**Add these imports:**
```python
from backend.routes.auth import router as auth_router
```

**Register router:**
```python
# Add this after existing router registrations
app.include_router(auth_router)
```

**Implementation:**
- [ ] Add import statement
- [ ] Register auth router with FastAPI app
- [ ] Restart FastAPI server
- [ ] Verify routes at http://localhost:8000/docs

**Expected API Docs:**
- `/api/auth/microsoft` (POST)
- `/api/auth/profile` (GET)
- `/api/auth/refresh` (POST)
- `/api/auth/verify` (GET)

---

#### Task 3.8: Protect Existing Routes (OPTIONAL - Phase 2)

**Purpose:** Add authentication requirement to existing job endpoints

**Routes to protect:**
- `POST /api/jobs/start` - Only authenticated users can start jobs
- `POST /api/jobs/{id}/approve` - Only authenticated users can approve data

**Implementation (OPTIONAL):**
```python
from backend.middleware.auth import get_current_user
from fastapi import Depends

@app.post("/api/jobs/start")
async def start_job(current_user: dict = Depends(get_current_user)):
    # Existing logic...
    pass
```

**Decision:**
- [ ] Decide if auth should be required for job operations
- [ ] If yes, add `Depends(get_current_user)` to endpoints
- [ ] If no, keep endpoints public (current behavior)

**Note:** Can be implemented later without breaking existing functionality.

---

### Phase 4: Frontend Implementation

All files can be copied from PDF Orders app with **one key difference**: Environment variable names.

#### Task 4.1: Install MSAL Package

**Command:**
```bash
cd frontend
npm install @azure/msal-browser
```

**Verification:**
```bash
npm list @azure/msal-browser
# Should show: @azure/msal-browser@3.x.x
```

**Implementation:**
- [ ] Install package
- [ ] Verify in `frontend/package.json` dependencies

---

#### Task 4.2: Create Frontend Directory Structure

**Create these directories:**
```bash
mkdir -p frontend/src/context
mkdir -p frontend/src/services
```

**Verification:**
- [ ] `frontend/src/context/` exists
- [ ] `frontend/src/services/` exists

---

#### Task 4.3: Create MSAL Configuration

**Source:** `pdf_orders/frontend/src/utils/msalConfig.ts` (or `.js`)
**Destination:** `frontend/src/utils/msalConfig.ts`

**Purpose:**
- MSAL instance configuration
- Login scopes
- Cache configuration

**CRITICAL CHANGE REQUIRED:**

**PDF Orders uses (Create React App):**
```typescript
const clientId = process.env.REACT_APP_AZURE_CLIENT_ID;
const tenantId = process.env.REACT_APP_AZURE_TENANT_ID;
```

**Text Orders must use (Vite):**
```typescript
const clientId = import.meta.env.VITE_AZURE_CLIENT_ID;
const tenantId = import.meta.env.VITE_AZURE_TENANT_ID;
```

**Implementation:**
- [ ] Copy `msalConfig.ts` from PDF Orders
- [ ] **REPLACE** `process.env.REACT_APP_*` with `import.meta.env.VITE_*`
- [ ] Verify redirect URIs: `http://localhost:5173` (not 5174 or other port)
- [ ] Export `msalInstance` and `loginRequest`

**Reference:** [pdf_orders/frontend/src/utils/msalConfig.ts](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/frontend/src/utils/)

---

#### Task 4.4: Create Microsoft Auth Service

**Source:** `pdf_orders/frontend/src/services/microsoftAuthService.ts`
**Destination:** `frontend/src/services/microsoftAuthService.ts`

**Purpose:**
- Sign in with popup/redirect
- Get access token
- Sign out

**Key Functions:**
- `signInWithPopup() -> AuthenticationResult`
- `signInWithRedirect()`
- `handleRedirectResponse() -> AuthenticationResult | null`
- `getAccessToken() -> string`
- `signOut()`

**Implementation:**
- [ ] Copy `microsoftAuthService.ts` from PDF Orders
- [ ] Verify imports use `msalInstance` from `utils/msalConfig.ts`
- [ ] No other modifications needed

**Reference:** [pdf_orders/frontend/src/services/microsoftAuthService.ts](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/frontend/src/services/)

---

#### Task 4.5: Create Auth Service

**Source:** `pdf_orders/frontend/src/services/authService.ts`
**Destination:** `frontend/src/services/authService.ts`

**Purpose:**
- Backend authentication (call `/api/auth/microsoft`)
- Token storage (localStorage)
- API calls with Authorization header

**Key Functions:**
- `authenticateWithBackend(accessToken: string, account: object) -> AuthResponse`
- `getStoredToken() -> string | null`
- `getStoredUser() -> User | null`
- `clearAuth()`

**CHANGE REQUIRED:**

**PDF Orders:**
```typescript
const API_URL = process.env.REACT_APP_API_URL;
```

**Text Orders:**
```typescript
const API_URL = import.meta.env.VITE_API_URL;
```

**Implementation:**
- [ ] Copy `authService.ts` from PDF Orders
- [ ] **REPLACE** `process.env.REACT_APP_API_URL` with `import.meta.env.VITE_API_URL`
- [ ] Verify backend endpoint: `/api/auth/microsoft`
- [ ] Verify localStorage keys: `auth_token`, `user_data`

**Reference:** [pdf_orders/frontend/src/services/authService.ts](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/frontend/src/services/)

---

#### Task 4.6: Create Auth Context

**Source:** `pdf_orders/frontend/src/context/AuthContext.tsx`
**Destination:** `frontend/src/context/AuthContext.tsx`

**Purpose:**
- Global auth state management
- Login/logout functions
- User state

**Context Exports:**
- `AuthProvider` - Wrap app
- `useAuth()` - Hook to access auth state
- State: `user`, `isAuthenticated`, `isLoading`, `error`
- Functions: `login()`, `logout()`, `refreshUser()`

**CHANGE REQUIRED:**

**PDF Orders:**
```typescript
const apiUrl = process.env.REACT_APP_API_URL;
```

**Text Orders:**
```typescript
const apiUrl = import.meta.env.VITE_API_URL;
```

**Implementation:**
- [ ] Copy `AuthContext.tsx` from PDF Orders
- [ ] **REPLACE** `process.env.REACT_APP_*` with `import.meta.env.VITE_*`
- [ ] Verify integration with `microsoftAuthService` and `authService`
- [ ] Export `AuthProvider` and `useAuth`

**Reference:** [pdf_orders/frontend/src/context/AuthContext.tsx](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/frontend/src/context/)

---

#### Task 4.7: Create Login Page Component

**Source:** `pdf_orders/frontend/src/components/LoginPage.tsx` (or similar)
**Destination:** `frontend/src/components/LoginPage.tsx`

**Purpose:**
- Login UI with Microsoft login button
- Handle auth flow
- Show loading/error states

**Key Features:**
- Microsoft login button
- Error handling UI
- Loading spinner
- Redirect after successful login

**Implementation:**
- [ ] Copy LoginPage component from PDF Orders
- [ ] Verify it uses `useAuth()` hook
- [ ] Adjust styling to match Text Orders UI (if needed)
- [ ] Use existing Shadcn UI components (Button, Card, etc.)

**Note:** May be named `LoginForm.tsx` or `Login.tsx` in PDF Orders.

**Reference:** [pdf_orders/frontend/src/components/](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/frontend/src/components/)

---

#### Task 4.8: Create Protected Route Component

**Source:** `pdf_orders/frontend/src/components/ProtectedRoute.tsx`
**Destination:** `frontend/src/components/ProtectedRoute.tsx`

**Purpose:**
- Wrapper component for protected routes
- Redirect to login if not authenticated
- Show loading state during auth check

**Usage Example:**
```tsx
<ProtectedRoute>
  <Dashboard />
</ProtectedRoute>
```

**Implementation:**
- [ ] Copy `ProtectedRoute.tsx` from PDF Orders
- [ ] Verify it uses `useAuth()` hook
- [ ] Verify redirect path: `/login`
- [ ] No modifications needed

**Reference:** [pdf_orders/frontend/src/components/ProtectedRoute.tsx](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/frontend/src/components/)

---

#### Task 4.9: Update App.tsx with Auth

**File:** `frontend/src/App.tsx`

**Changes Required:**

1. **Import AuthProvider:**
```tsx
import { AuthProvider } from './context/AuthContext';
```

2. **Wrap app with AuthProvider:**
```tsx
<AuthProvider>
  <BrowserRouter>
    {/* existing routes */}
  </BrowserRouter>
</AuthProvider>
```

3. **Add login route:**
```tsx
<Route path="/login" element={<LoginPage />} />
```

4. **Protect existing routes (OPTIONAL):**
```tsx
<Route path="/order-processing" element={
  <ProtectedRoute>
    <Dashboard />
  </ProtectedRoute>
} />
```

**Implementation:**
- [ ] Add AuthProvider wrapper
- [ ] Add login route
- [ ] Import LoginPage and ProtectedRoute
- [ ] Decide which routes to protect (can do later)

**Reference:** [pdf_orders/frontend/src/App.tsx](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/frontend/src/App.tsx:1-50)

---

#### Task 4.10: Update API Client with Auth Headers

**File:** `frontend/src/api/jobsApi.ts`

**Changes Required:**

1. **Import auth service:**
```typescript
import { getStoredToken } from '../services/authService';
```

2. **Add Authorization header to requests:**
```typescript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

// Add request interceptor
api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor (handle 401)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      clearAuth();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

**Implementation:**
- [ ] Add request interceptor for Authorization header
- [ ] Add response interceptor for 401 handling
- [ ] Use axios instance for all API calls
- [ ] Test with protected endpoints

**Note:** Only needed if backend routes are protected. Can skip if keeping routes public.

---

### Phase 5: Testing & Verification

#### Task 5.1: Backend Testing

**Tests to perform:**

1. **JWT Secret Verification:**
```bash
# Check .env has JWT_SECRET set
grep JWT_SECRET .env
```

2. **Backend Server Start:**
```bash
cd backend
uvicorn main:app --reload --port 8000
# Should start without errors
```

3. **API Documentation:**
- Visit: http://localhost:8000/docs
- Verify auth endpoints exist:
  - `POST /api/auth/microsoft`
  - `GET /api/auth/profile`
  - `POST /api/auth/refresh`
  - `GET /api/auth/verify`

4. **Database Connection:**
```bash
# Verify users table exists
psql $DATABASE_URL -c "\dt users"
```

**Checklist:**
- [ ] Backend starts without errors
- [ ] Auth endpoints visible in /docs
- [ ] Users table exists in database
- [ ] JWT_SECRET is set and loaded

---

#### Task 5.2: Frontend Testing

**Tests to perform:**

1. **Frontend Build:**
```bash
cd frontend
npm run build
# Should compile without TypeScript errors
```

2. **Frontend Dev Server:**
```bash
npm run dev
# Should start at http://localhost:5173
```

3. **Environment Variables:**
```bash
# In browser console (on http://localhost:5173):
console.log(import.meta.env.VITE_AZURE_CLIENT_ID)
console.log(import.meta.env.VITE_AZURE_TENANT_ID)
console.log(import.meta.env.VITE_API_URL)
# All should return values
```

4. **MSAL Configuration:**
- Check browser console for MSAL initialization errors
- Should see no errors related to MSAL

**Checklist:**
- [ ] Frontend builds successfully
- [ ] Dev server starts at port 5173
- [ ] Environment variables accessible
- [ ] No console errors

---

#### Task 5.3: Authentication Flow Testing

**Full end-to-end test:**

1. **Navigate to login page:**
   - Go to: http://localhost:5173/login
   - Verify "Sign in with Microsoft" button appears

2. **Click login button:**
   - Click button
   - Microsoft popup should appear
   - Login with Office 365 credentials

3. **Verify authentication:**
   - Check browser localStorage:
     - `auth_token` should exist
     - `user_data` should exist
   - Check browser console for any errors

4. **Test backend token:**
   - Open http://localhost:8000/docs
   - Click `/api/auth/profile` endpoint
   - Click "Try it out"
   - Add Authorization header: `Bearer <your-token-from-localStorage>`
   - Execute
   - Should return user profile

5. **Test protected routes:**
   - Navigate to protected route (e.g., `/order-processing`)
   - Should allow access (not redirect to login)

6. **Test logout:**
   - Call logout function
   - Verify localStorage cleared
   - Verify redirect to login page

**Checklist:**
- [ ] Login popup works
- [ ] Token stored in localStorage
- [ ] Backend accepts token
- [ ] Protected routes accessible
- [ ] Logout works

---

#### Task 5.4: Error Handling Testing

**Test these scenarios:**

1. **Invalid Token:**
   - Manually corrupt token in localStorage
   - Refresh page
   - Should redirect to login

2. **Expired Token:**
   - Wait for token to expire (or manually set old timestamp)
   - Make API request
   - Should get 401 error and redirect to login

3. **Network Errors:**
   - Stop backend server
   - Try to login
   - Should show error message

4. **Microsoft Auth Errors:**
   - Cancel Microsoft popup
   - Should show error message (not crash)

**Checklist:**
- [ ] Invalid token handled gracefully
- [ ] Expired token redirects to login
- [ ] Network errors show user-friendly message
- [ ] Auth cancellation doesn't crash app

---

## 🔄 AUTHENTICATION FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER CLICKS "SIGN IN WITH MICROSOFT"                        │
│    Frontend: MSAL popup initiated                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. MICROSOFT AUTHENTICATION                                     │
│    User enters O365 credentials                                 │
│    Microsoft validates and returns access token                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. FRONTEND RECEIVES MICROSOFT TOKEN                            │
│    MSAL: Stores Microsoft token                                 │
│    Frontend: Calls POST /api/auth/microsoft                     │
│    Payload: { accessToken, account }                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. BACKEND VERIFIES MICROSOFT TOKEN                             │
│    Middleware: Calls Microsoft Graph API /me endpoint           │
│    Microsoft: Returns user profile (email, name, etc.)          │
│    Backend: Validates response                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. BACKEND CREATES/UPDATES USER                                 │
│    Service: Checks if user exists by email                      │
│    Service: Creates user if new, updates if exists              │
│    Database: INSERT/UPDATE users table                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. BACKEND GENERATES JWT TOKEN                                  │
│    Utils: Creates token payload (user id, email, etc.)          │
│    Utils: Signs token with JWT_SECRET                           │
│    Token expires in 24 hours (configurable)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. BACKEND RETURNS JWT + USER DATA                              │
│    Response: { success, data: { user, token, expiresIn } }      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. FRONTEND STORES AUTH DATA                                    │
│    localStorage: Set 'auth_token'                               │
│    localStorage: Set 'user_data'                                │
│    Context: Update auth state (isAuthenticated = true)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. SUBSEQUENT API REQUESTS                                      │
│    Frontend: Adds header "Authorization: Bearer <jwt_token>"    │
│    Backend: Verifies JWT on protected routes                    │
│    Backend: Attaches user info to request                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 FILE STRUCTURE COMPARISON

### Current State (Text Orders - Before Implementation)

```
text_orders/
├── backend/
│   ├── utils/
│   │   ├── anthropic_helper.py
│   │   ├── database.py
│   │   └── logger.py
│   ├── tasks/
│   ├── subagents/
│   └── main.py
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── hooks/
│       ├── types/
│       └── utils/
└── .env
```

### After Implementation (Text Orders - Target State)

```
text_orders/
├── backend/
│   ├── utils/
│   │   ├── anthropic_helper.py
│   │   ├── database.py
│   │   ├── logger.py
│   │   └── auth.py ✨ NEW
│   ├── middleware/ ✨ NEW
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── microsoft_auth.py
│   ├── services/ ✨ NEW
│   │   ├── __init__.py
│   │   └── user_service.py
│   ├── routes/ ✨ NEW
│   │   ├── __init__.py
│   │   └── auth.py
│   ├── tasks/
│   ├── subagents/
│   └── main.py (updated)
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       │   ├── LoginPage.tsx ✨ NEW
│       │   └── ProtectedRoute.tsx ✨ NEW
│       ├── context/ ✨ NEW
│       │   └── AuthContext.tsx
│       ├── services/ ✨ NEW
│       │   ├── authService.ts
│       │   └── microsoftAuthService.ts
│       ├── hooks/
│       ├── types/
│       └── utils/
│           └── msalConfig.ts ✨ NEW
├── .env (JWT_SECRET added)
└── postgres_schema/
    └── create_users_table.sql ✨ NEW
```

---

## 📊 IMPLEMENTATION METRICS

**Estimated Implementation Time:**
- Phase 1 (Database): 15 minutes
- Phase 2 (Dependencies): 5 minutes
- Phase 3 (Backend): 1 hour (mostly copy-paste)
- Phase 4 (Frontend): 1.5 hours (copy-paste + env var updates)
- Phase 5 (Testing): 30 minutes
- **Total: ~3 hours**

**Files to Create:**
- Backend: 7 new files
- Frontend: 5 new files
- Database: 1 SQL script
- **Total: 13 new files**

**Dependencies to Add:**
- Backend: 2 packages (`python-jose`, `passlib`)
- Frontend: 1 package (`@azure/msal-browser`)

---

## 🚨 COMMON PITFALLS & SOLUTIONS

### Pitfall 1: Wrong Environment Variable Prefix

**Problem:** Using `process.env.REACT_APP_*` in Vite app
**Error:** `undefined` values for client ID and tenant ID
**Solution:** Use `import.meta.env.VITE_*` in all frontend files

### Pitfall 2: Azure App Registration Platform Type

**Problem:** App configured as "Web" instead of "SPA"
**Error:** `AADSTS9002326: Cross-origin token redemption is permitted only for the 'Single-Page Application' client-type`
**Solution:** Change platform type to "Single-page application" in Azure Portal

### Pitfall 3: Missing JWT_SECRET

**Problem:** JWT_SECRET not set in .env
**Error:** Backend fails to generate tokens
**Solution:** Generate secure random string and add to `.env`

### Pitfall 4: CORS Issues

**Problem:** Frontend can't call backend API
**Error:** CORS policy blocked request
**Solution:** Verify FastAPI CORS middleware allows `http://localhost:5173`

### Pitfall 5: Token Not Sent in Requests

**Problem:** API returns 401 even after login
**Error:** "Authorization header missing"
**Solution:** Add axios interceptor to include Authorization header

### Pitfall 6: Database Connection String

**Problem:** User service can't connect to database
**Error:** "Connection refused" or "Database error"
**Solution:** Verify `DATABASE_URL` in .env is correct and database is running

---

## 🔒 SECURITY CHECKLIST

- [ ] JWT_SECRET is minimum 32 characters, randomly generated
- [ ] JWT_SECRET is not committed to version control
- [ ] Tokens expire after 24 hours (or shorter for production)
- [ ] HTTPS used in production (not HTTP)
- [ ] Authorization header uses Bearer token format
- [ ] User passwords are NOT stored (using Microsoft auth only)
- [ ] API permissions use principle of least privilege
- [ ] CORS only allows trusted origins
- [ ] SQL queries use parameterized statements (no injection)
- [ ] Error messages don't leak sensitive information

---

## 📚 REFERENCE DOCUMENTATION

### Microsoft Documentation
- [MSAL.js Browser Library](https://github.com/AzureAD/microsoft-authentication-library-for-js/tree/dev/lib/msal-browser)
- [Azure AD App Registration](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/overview)

### Internal References
- **Source App:** `C:\Users\AI_USER\Desktop\Scripts\OrderIntake_web_app\pdf_orders`
- **Backend Auth:** [pdf_orders/backend/routes/auth.py](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/backend/routes/auth.py)
- **Frontend Auth:** [pdf_orders/frontend/src/context/AuthContext.tsx](file:///C:/Users/AI_USER/Desktop/Scripts/OrderIntake_web_app/pdf_orders/frontend/src/context/)

### Related Documentation
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- JWT.io: https://jwt.io/
- Python-JOSE: https://python-jose.readthedocs.io/

---

## ✅ IMPLEMENTATION COMPLETION CHECKLIST

### Pre-Implementation:
- [ ] JWT_SECRET generated and added to `.env`
- [ ] Azure App Registration verified as SPA type
- [ ] Redirect URIs configured correctly
- [ ] API permissions granted

### Phase 1 - Database:
- [ ] Users table created
- [ ] Table verified in PostgreSQL

### Phase 2 - Dependencies:
- [ ] `requirements.txt` updated
- [ ] Python packages installed
- [ ] `package.json` updated
- [ ] NPM packages installed

### Phase 3 - Backend:
- [ ] `backend/utils/auth.py` created
- [ ] `backend/middleware/auth.py` created
- [ ] `backend/middleware/microsoft_auth.py` created
- [ ] `backend/services/user_service.py` created
- [ ] `backend/routes/auth.py` created
- [ ] Auth routes registered in `main.py`
- [ ] Backend starts without errors

### Phase 4 - Frontend:
- [ ] `frontend/src/utils/msalConfig.ts` created (env vars updated)
- [ ] `frontend/src/services/microsoftAuthService.ts` created
- [ ] `frontend/src/services/authService.ts` created (env vars updated)
- [ ] `frontend/src/context/AuthContext.tsx` created (env vars updated)
- [ ] `frontend/src/components/LoginPage.tsx` created
- [ ] `frontend/src/components/ProtectedRoute.tsx` created
- [ ] `App.tsx` updated with AuthProvider
- [ ] Login route added
- [ ] Frontend builds without errors

### Phase 5 - Testing:
- [ ] Login flow works end-to-end
- [ ] Token stored in localStorage
- [ ] Protected routes work
- [ ] Logout works
- [ ] Error handling tested

### Documentation:
- [ ] Update `Communication.md` with implementation status
- [ ] Document any deviations from this plan
- [ ] Note any production-specific changes needed

---

## 📞 SUPPORT & TROUBLESHOOTING

### If Login Fails:

1. **Check Browser Console:**
   - Look for MSAL errors
   - Check network requests to `/api/auth/microsoft`
   - Verify environment variables are loaded

2. **Check Backend Logs:**
   - Look for Microsoft Graph API errors
   - Check JWT generation errors
   - Verify database connection

3. **Check Azure Portal:**
   - Verify app registration settings
   - Check redirect URIs
   - Verify API permissions granted

4. **Common Fixes:**
   - Clear localStorage and try again
   - Restart backend server
   - Verify .env files loaded correctly
   - Check network connectivity

---

## 🎉 FINAL NOTES

**Key Success Factors:**
1. Copy files from PDF Orders (don't rewrite from scratch)
2. Update `REACT_APP_*` to `VITE_*` in frontend files
3. Generate strong JWT_SECRET
4. Test each phase before moving to next
5. Use PDF Orders as reference for any questions

**Post-Implementation:**
- Monitor authentication errors in production
- Rotate JWT_SECRET quarterly
- Review API permissions regularly
- Update MSAL package as new versions release

**Production Deployment:**
- Add production redirect URIs to Azure App Registration
- Use environment-specific JWT_SECRET values
- Enable HTTPS for all endpoints
- Configure production CORS settings
- Set shorter token expiration (consider 1-4 hours)

---

**Document Version:** 1.0
**Created:** 2025-11-20
**Author:** Claude Code
**Status:** Ready for Implementation
**Next Action:** Generate JWT_SECRET and begin Phase 1
