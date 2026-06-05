# Rhythm SoulVerse API — Railway Deployment

## Deploy in 3 minutes (no coding needed)

### Step 1: Create GitHub account
- Go to github.com → Sign up (free)

### Step 2: Upload this folder to GitHub
- github.com → New repository → Name: soulverse-api
- Upload all files from this folder

### Step 3: Deploy on Railway
- Go to railway.app → Login with GitHub
- New Project → Deploy from GitHub repo → Select soulverse-api
- Add variable: ANTHROPIC_API_KEY = your key
- Deploy! Live in 2 minutes.

## Endpoints
- GET  /health — health check
- GET  /docs — Swagger API documentation
- POST /v1/auth/register
- POST /v1/auth/verify-otp  (demo OTP: 123456)
- GET  /v1/astrology/horoscope/daily
- POST /v1/numerology/generate
- POST /v1/ayurveda/assessment
- GET  /v1/meditation/library
- POST /v1/ai/chat  (uses Claude if ANTHROPIC_API_KEY set)
- GET  /v1/experts
- POST /v1/bookings
- GET  /v1/admin/dashboard
