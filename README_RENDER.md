# Deploy on Render

This project is best deployed on Render as two services:

1. `pcos-backend` as a Docker Web Service
2. `pcos-frontend` as a Static Site

## Why Docker for backend?
Stage 2 OCR needs `tesseract-ocr`, and the included Dockerfile installs it for Linux.

## Backend service
Create a new **Web Service** on Render.

Settings:
- Environment: `Docker`
- Root Directory: leave blank (repo root)
- Dockerfile Path: `backend/Dockerfile`
- Name: `pcos-backend`

After deploy, open the backend URL and test:
- `/health`
- `/predict`
- `/predict-stage2`
- `/upload-stage2-report`

Example health URL:
- `https://your-backend-name.onrender.com/health`

## Frontend service
Create a new **Static Site** on Render.

Settings:
- Root Directory: `frontend`
- Build Command: `npm install && npm run build`
- Publish Directory: `dist`

Environment variable:
- Key: `VITE_API_BASE_URL`
- Value: your backend public URL, for example:
- `https://your-backend-name.onrender.com`

## Important note
The frontend uses `VITE_API_BASE_URL`. Without setting it, the deployed site will still try to call local development URLs.

## Local development
Create `frontend/.env` from `frontend/.env.example` if needed.

Example:
```env
VITE_API_BASE_URL=http://127.0.0.1:5000
```

## Files added for deployment
- `backend/Dockerfile`
- `frontend/.env.example`

## Backend runtime details
The backend now:
- reads `PORT` from the environment
- binds to `0.0.0.0`
- supports Linux Tesseract paths
- still works on Windows locally
