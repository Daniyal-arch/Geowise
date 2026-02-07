# 🚀 GEOWISE Deployment Guide

This guide walks you through deploying GEOWISE with:
- **Backend** on Render (Free tier)
- **Frontend** on Vercel (Free tier)

---

## 📋 Prerequisites

Before you start, make sure you have:
- [ ] GitHub account
- [ ] Render account (sign up at [render.com](https://render.com))
- [ ] Vercel account (sign up at [vercel.com](https://vercel.com))
- [ ] Your API keys ready:
  - NASA FIRMS API Key
  - Global Forest Watch API Key
  - Groq API Key

---

## Part 1: Deploy Backend to Render

### Step 1: Push Code to GitHub

```bash
# Make sure your code is committed and pushed
git add .
git commit -m "Add deployment configurations"
git push origin main
```

### Step 2: Create Render Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select your `geowise` repository

### Step 3: Configure Service Settings

Render will auto-detect the `render.yaml` file, but verify these settings:

| Setting | Value |
|---------|-------|
| **Name** | `geowise-backend` (or your choice) |
| **Region** | Oregon (US West) or closest to you |
| **Branch** | `main` |
| **Root Directory** | Leave empty |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free |

### Step 4: Add Environment Variables

In the Render dashboard, go to **Environment** tab and add:

```bash
# Required API Keys
NASA_FIRMS_API_KEY=your_nasa_firms_key_here
GFW_API_KEY=your_gfw_key_here
GROQ_API_KEY=your_groq_key_here

# App Configuration (auto-populated from render.yaml, verify these exist)
APP_NAME=GEOWISE API
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///./geowise.db
```

**⚠️ Important Notes:**
- Don't use the keys from `backend/.env` if they're test keys
- Get production keys from respective services:
  - NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/api/
  - Groq: https://console.groq.com/keys
  - GFW: Already provided in your config

### Step 5: Deploy

1. Click **"Create Web Service"**
2. Wait 5-10 minutes for build to complete
3. Once deployed, you'll get a URL like: `https://geowise-backend.onrender.com`

### Step 6: Test Backend

Visit these URLs to verify:
- Health check: `https://your-app.onrender.com/health`
- API docs: `https://your-app.onrender.com/docs`

**⚠️ Free Tier Limitation:**
- Render free tier **spins down after 15 minutes** of inactivity
- First request after spin-down will take 30-60 seconds (cold start)
- This is normal for free tier

---

## Part 2: Deploy Frontend to Vercel

### Step 1: Prepare Frontend

Make sure your frontend code is in the `frontend/` directory and pushed to GitHub.

### Step 2: Import Project to Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **"Add New"** → **"Project"**
3. Import your `geowise` repository from GitHub

### Step 3: Configure Project Settings

| Setting | Value |
|---------|-------|
| **Framework Preset** | Next.js |
| **Root Directory** | `frontend` ← **IMPORTANT!** |
| **Build Command** | `npm run build` (auto-detected) |
| **Output Directory** | `.next` (auto-detected) |
| **Install Command** | `npm install` (auto-detected) |

### Step 4: Add Environment Variables

In the project settings, add environment variables:

```bash
# Backend API URL (use your Render URL from Part 1)
NEXT_PUBLIC_API_URL=https://your-render-app.onrender.com/api/v1

# App Info
NEXT_PUBLIC_APP_NAME=GEOWISE
NEXT_PUBLIC_APP_VERSION=0.1.0
NEXT_PUBLIC_ENVIRONMENT=production
```

**Replace** `your-render-app.onrender.com` with your actual Render backend URL!

### Step 5: Deploy

1. Click **"Deploy"**
2. Wait 2-3 minutes for build
3. You'll get a URL like: `https://geowise.vercel.app`

### Step 6: Test Frontend

1. Visit your Vercel URL
2. Try the natural language query feature
3. Check if maps load correctly

---

## Part 3: Connect Frontend & Backend

### Update CORS on Backend

After deploying frontend, you need to allow requests from your Vercel domain.

#### Option A: Update via Render Dashboard

1. Go to Render → Your Service → Environment
2. Find `ALLOWED_ORIGINS` variable
3. Change from `*` to your Vercel URL:
   ```
   https://geowise.vercel.app
   ```
4. Save and redeploy

#### Option B: Update in Code

Edit [app/main.py:26-31](app/main.py#L26-L31) and update CORS:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://geowise.vercel.app"],  # Your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then commit and push to trigger redeployment.

---

## 🎯 Post-Deployment Checklist

- [ ] Backend health check returns 200 OK
- [ ] Backend API docs accessible at `/docs`
- [ ] Frontend loads without errors
- [ ] Frontend can fetch data from backend
- [ ] Maps render correctly
- [ ] Natural language queries work
- [ ] Fire detection queries work
- [ ] No CORS errors in browser console

---

## 🐛 Troubleshooting

### Backend Issues

**Problem: Build fails with "No module named 'app'"**
- Solution: Make sure `Root Directory` is empty (not `backend/`)

**Problem: "Database is locked" errors**
- Solution: SQLite works fine on Render. If you see this, it's due to concurrent requests. Consider adding retry logic or switch to PostgreSQL.

**Problem: Large dependencies timeout during build**
- Solution: Render free tier has 15-minute build limit. Your geospatial libs are large. If timeout occurs:
  - Remove unused dependencies from `requirements.txt`
  - Or upgrade to Render paid plan ($7/month for faster builds)

**Problem: Cold starts are slow (30-60s)**
- Solution: This is normal for free tier. Upgrade to paid plan for always-on instances.

### Frontend Issues

**Problem: "Failed to fetch" errors in console**
- Solution: Check `NEXT_PUBLIC_API_URL` environment variable in Vercel
- Make sure it points to your Render backend URL
- Check CORS settings on backend

**Problem: Maps don't load**
- Solution: Check browser console for errors
- Verify MapLibre dependencies are installed
- Check if API keys are working

**Problem: Build fails with "Module not found"**
- Solution: Make sure `Root Directory` is set to `frontend`
- Verify all dependencies are in `frontend/package.json`

### CORS Issues

**Problem: "CORS policy blocked" errors**
- Solution: Update `ALLOWED_ORIGINS` in Render environment variables
- Or update `app/main.py` CORS settings to include your Vercel URL

---

## 💰 Cost Breakdown

| Service | Free Tier Limits | Estimated Cost |
|---------|------------------|----------------|
| **Render** | 750 hours/month, spins down after 15min | **$0** |
| **Vercel** | 100GB bandwidth, unlimited deployments | **$0** |
| **NASA FIRMS** | Free tier (rate limited) | **$0** |
| **Groq** | Free tier (rate limited) | **$0** |
| **GFW** | Free | **$0** |
| **TOTAL** | | **$0/month** |

---

## 🚀 Production Recommendations

For production use, consider:

1. **Upgrade Render to paid plan** ($7/month) for:
   - Always-on instances (no cold starts)
   - Better performance
   - More resources

2. **Add PostgreSQL** instead of SQLite:
   - Better for concurrent requests
   - Render offers free PostgreSQL (256MB)
   - Or use [Supabase](https://supabase.com) free tier (500MB)

3. **Add Redis for caching**:
   - Use [Upstash](https://upstash.com) free tier
   - 10K commands/day free

4. **Set up custom domain**:
   - Add custom domain in Vercel (free)
   - Add custom domain in Render (free)

5. **Enable monitoring**:
   - Render has built-in metrics
   - Vercel has analytics (free tier available)

---

## 📞 Need Help?

- Render Docs: https://render.com/docs
- Vercel Docs: https://vercel.com/docs
- GEOWISE Issues: https://github.com/yourusername/geowise/issues

---

## 🎉 You're Done!

Your GEOWISE app should now be live at:
- Frontend: `https://your-app.vercel.app`
- Backend: `https://your-app.onrender.com`

Share your deployment and start analyzing geospatial data! 🌍✨
