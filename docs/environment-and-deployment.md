# Environment variables

## Frontend (`.env.local` / Vercel)

```env
AGENT_VPS_URL=https://your-vps-ip-or-domain:8000
```

## Backend (`.env` on VPS)

```env
GEMINI_API_KEY=your-gemini-api-key

# Optional Google integrations (Calendar + Maps account connect)
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
GOOGLE_OAUTH_REDIRECT_URI=https://your-backend-domain/integrations/google/callback
# GOOGLE_OAUTH_SCOPES=https://www.googleapis.com/auth/calendar,https://www.googleapis.com/auth/calendar.events
```

---

# Deployment checklist

## Frontend (Vercel)

- [ ] Push to GitHub
- [ ] Connect repo to Vercel
- [ ] Set `AGENT_VPS_URL` env var
- [ ] Deploy
- [ ] Test on mobile
- [ ] Share URL

## Backend (VPS)

- [ ] Install Python 3.11+
- [ ] `pip install -r requirements.txt`
- [ ] Set `GEMINI_API_KEY`
- [ ] (Optional) Set Google OAuth env vars for Calendar/Maps integrations
- [ ] Copy `skills/` directory
- [ ] Run: `uvicorn main:app --host 0.0.0.0 --port 8000`
- [ ] Test: `curl http://VPS_IP:8000/health`
- [ ] Ensure firewall allows port 8000 from Vercel (or use reverse proxy + HTTPS)
