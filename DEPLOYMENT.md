# 🚀 Deployment Guide - Streamlit Community Cloud

## Quick Deploy Steps

### 1. Create GitHub Repository

**Option A: Using GitHub Website**
1. Go to [github.com](https://github.com) and sign in
2. Click the **"+"** icon → **"New repository"**
3. Name it: `jv-matcher` (or your preferred name)
4. Choose **Public** (required for free Streamlit Cloud)
5. **Don't** initialize with README (we already have one)
6. Click **"Create repository"**

**Option B: Using GitHub CLI** (if installed)
```bash
gh repo create jv-matcher --public --source=. --remote=origin --push
```

### 2. Push Code to GitHub

```bash
# Add remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/jv-matcher.git

# Rename branch to main (if needed)
git branch -M main

# Push code
git push -u origin main
```

**If you get authentication errors:**
- Use a Personal Access Token instead of password
- Or use SSH: `git@github.com:YOUR_USERNAME/jv-matcher.git`

### 3. Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **"New app"**
4. Fill in:
   - **Repository:** Select `YOUR_USERNAME/jv-matcher`
   - **Branch:** `main`
   - **Main file:** `app.py`
   - **App URL:** (optional) Choose a custom subdomain
5. Click **"Deploy"**

### 4. Wait for Deployment

- First deployment takes 2-3 minutes
- Streamlit will install dependencies automatically
- You'll see build logs in real-time
- When done, you'll get a public URL like: `https://jv-matcher.streamlit.app`

## ✅ Verification Checklist

- [ ] Code pushed to GitHub
- [ ] Repository is Public (for free tier)
- [ ] `app.py` is in root directory
- [ ] `requirements.txt` includes all dependencies
- [ ] `.gitignore` excludes venv/ and outputs/
- [ ] Streamlit Cloud connected to GitHub
- [ ] App deployed successfully

## 🔧 Troubleshooting

### "Module not found" errors
- Check `requirements.txt` has all dependencies
- Ensure versions are specified (e.g., `streamlit>=1.28.0`)

### "File not found" errors
- Make sure all files are committed and pushed
- Check file paths are relative (not absolute)

### Build fails
- Check build logs in Streamlit Cloud dashboard
- Verify Python version compatibility
- Ensure `app.py` is the correct entry point

## 📝 Files Required for Deployment

These files must be in your repository:
- ✅ `app.py` - Main Streamlit app
- ✅ `jv_matcher.py` - Core engine
- ✅ `requirements.txt` - Dependencies
- ✅ `README.md` - Project description
- ✅ `.gitignore` - Excludes unnecessary files

## 🌐 After Deployment

Your app will be live at:
```
https://YOUR-APP-NAME.streamlit.app
```

Share this URL with your team!

## 🔄 Updating the App

1. Make changes locally
2. Commit: `git add . && git commit -m "Update description"`
3. Push: `git push`
4. Streamlit Cloud auto-deploys (takes ~1 minute)

---

**Need help?** Check [Streamlit Cloud docs](https://docs.streamlit.io/streamlit-community-cloud)




