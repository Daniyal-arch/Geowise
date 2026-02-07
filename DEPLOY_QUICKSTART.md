# ⚡ GEOWISE Quick Deploy

## 1️⃣ Deploy Backend (Render)

1. Push code to GitHub
2. Go to https://dashboard.render.com/
3. New + → Web Service → Connect your repo
4. Settings:
   - **Root Directory**: Leave empty
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   ```
   NASA_FIRMS_API_KEY=your_key
   GFW_API_KEY=your_key
   GROQ_API_KEY=your_key
   ```
6. Deploy → Get URL: `https://your-app.onrender.com`

## 2️⃣ Deploy Frontend (Vercel)

1. Go to https://vercel.com/dashboard
2. Add New → Project → Import your repo
3. Settings:
   - **Root Directory**: `frontend` ⚠️
   - Framework: Next.js (auto-detected)
4. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-render-app.onrender.com/api/v1
   ```
5. Deploy → Get URL: `https://your-app.vercel.app`

## 3️⃣ Update CORS

On Render, add environment variable:
```
ALLOWED_ORIGINS=https://your-app.vercel.app
```

## ✅ Done!

Test:
- Backend: https://your-app.onrender.com/docs
- Frontend: https://your-app.vercel.app

📖 Full guide: See [DEPLOYMENT.md](DEPLOYMENT.md)
