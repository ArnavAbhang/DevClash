<<<<<<< HEAD
# DevClash
Team Code Blooded
=======
# ✅ TaskApp — Full-Stack Task Manager

A production-ready full-stack web application built with React + Vite (frontend) and Node.js + Express + MongoDB (backend), featuring JWT authentication and full CRUD task management.

---

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Frontend   | React 19, Vite, Tailwind CSS        |
| Backend    | Node.js, Express.js                 |
| Database   | MongoDB + Mongoose                  |
| Auth       | JWT (JSON Web Tokens)               |
| HTTP       | Axios (frontend), REST API          |

---

## Project Structure

```
root/
├── backend/
│   ├── src/
│   │   ├── config/         # MongoDB connection
│   │   ├── controllers/    # Route handlers
│   │   ├── middleware/     # Auth, error handler, validation
│   │   ├── models/         # Mongoose schemas (User, Task)
│   │   ├── routes/         # Express routers
│   │   ├── services/       # Business logic
│   │   ├── utils/          # JWT helpers
│   │   ├── app.js          # Express app setup
│   │   └── server.js       # Entry point
│   ├── .env
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── components/     # Navbar, ProtectedRoute, TaskCard, TaskModal
│   │   ├── context/        # AuthContext
│   │   ├── hooks/          # useTasks
│   │   ├── pages/          # LoginPage, RegisterPage, DashboardPage
│   │   ├── services/       # api.js (Axios instance + API methods)
│   │   ├── utils/          # helpers.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── .env
│   └── package.json
├── .env
└── README.md
```

---

## Prerequisites

- **Node.js** v18+
- **MongoDB** running locally on port 27017 (or a MongoDB Atlas URI)

---

## Setup & Running

### 1. Clone and configure environment

Copy the root `.env` and update the values:

```bash
# backend/.env
PORT=5000
NODE_ENV=development
MONGO_URI=mongodb://localhost:27017/taskapp
JWT_SECRET=your_super_secret_key_here
JWT_EXPIRES_IN=7d
CLIENT_ORIGIN=http://localhost:5173
```

```bash
# frontend/.env
VITE_API_BASE_URL=http://localhost:5000/api
```

> **Important:** Change `JWT_SECRET` to a long, random string before deploying.

---

### 2. Install backend dependencies

```bash
cd backend
npm install
```

### 3. Start the backend

```bash
# Development (with auto-reload)
npm run dev

# Production
npm start
```

The API will be available at `http://localhost:5000`.

---

### 4. Install frontend dependencies

```bash
cd frontend
npm install
```

### 5. Start the frontend

```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## API Reference

### Auth

| Method | Endpoint             | Auth | Description          |
|--------|----------------------|------|----------------------|
| POST   | `/api/auth/register` | No   | Register new user    |
| POST   | `/api/auth/login`    | No   | Login, returns token |
| GET    | `/api/auth/me`       | Yes  | Get current user     |

### Tasks

| Method | Endpoint          | Auth | Description                        |
|--------|-------------------|------|------------------------------------|
| GET    | `/api/tasks`      | Yes  | Get all tasks (filter by status/priority) |
| POST   | `/api/tasks`      | Yes  | Create a task                      |
| GET    | `/api/tasks/:id`  | Yes  | Get a single task                  |
| PUT    | `/api/tasks/:id`  | Yes  | Update a task                      |
| DELETE | `/api/tasks/:id`  | Yes  | Delete a task                      |

Query params for `GET /api/tasks`: `?status=todo|in-progress|done` and `?priority=low|medium|high`

---

## Features

- JWT authentication with token stored in `localStorage`
- Automatic token attachment via Axios request interceptor
- Auto-redirect to `/login` on 401 responses
- Session restoration on page refresh (via `/api/auth/me`)
- Task CRUD with status and priority filtering
- Global error handler with Mongoose-aware error mapping
- Input validation on both frontend and backend
- Responsive UI with Tailwind CSS
- Accessible forms and modals (ARIA labels, roles)

---

## Security Notes

- Passwords are hashed with bcrypt (12 salt rounds)
- JWT secret must be set via environment variable — never hardcoded
- CORS is restricted to the configured `CLIENT_ORIGIN`
- Passwords are excluded from all query results by default (`select: false`)
- All task operations are scoped to the authenticated user
>>>>>>> 221c088 (commit)
