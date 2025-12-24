# Google Docs Setup Guide for JARVIS

This guide walks you through setting up Google Docs integration for the Research & Paper Writing module.

## Overview

JARVIS can create formatted research papers directly in Google Docs. This requires:
1. A Google Cloud project with Docs and Drive APIs enabled
2. OAuth 2.0 credentials for desktop application
3. One-time authorization in your browser

**Time required:** ~10 minutes

---

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top → **New Project**
3. Name it something like "JARVIS Assistant"
4. Click **Create**
5. Wait for the project to be created, then select it

---

## Step 2: Enable Required APIs

1. In the left sidebar, go to **APIs & Services** → **Library**
2. Search for and enable these APIs:
   - **Google Docs API** - Click it, then click **Enable**
   - **Google Drive API** - Click it, then click **Enable**

---

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** (unless you have a Google Workspace account)
3. Click **Create**
4. Fill in the required fields:
   - **App name:** JARVIS
   - **User support email:** Your email
   - **Developer contact email:** Your email
5. Click **Save and Continue**
6. On the **Scopes** page, click **Add or Remove Scopes**
7. Add these scopes:
   - `https://www.googleapis.com/auth/documents`
   - `https://www.googleapis.com/auth/drive.file`
8. Click **Update**, then **Save and Continue**
9. On **Test users**, click **Add Users** and add your Gmail address
10. Click **Save and Continue**, then **Back to Dashboard**

---

## Step 4: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Desktop app** as the application type
4. Name it "JARVIS Desktop"
5. Click **Create**
6. Click **Download JSON** on the popup
7. Save the file as `google_credentials.json` in your JARVIS `config/` folder

Your file structure should look like:
```
Jarvis/
├── config/
│   ├── google_credentials.json  ← Put the file here
│   ├── settings.yaml
│   └── ...
```

---

## Step 5: First-Time Authorization

1. Run JARVIS: `python run.py --text`
2. Say: "Write a research paper on artificial intelligence"
3. A browser window will open asking you to sign in to Google
4. Sign in with your Google account
5. Click **Continue** (you may see a warning since the app isn't verified - this is normal for personal projects)
6. Click **Allow** to grant JARVIS access to create documents
7. The browser will show "Authentication successful" - you can close it
8. JARVIS will save a token file (`config/google_token.json`) for future use

---

## Verification

To verify Google Docs is configured correctly:

```bash
python run.py --text
```

Then say: "Check Google Docs setup"

You should see:
```
✅ Google Docs: Configured
   - Credentials: Found
   - Token: Valid
   - Test document: Created successfully
```

---

## Troubleshooting

### "Credentials file not found"
- Make sure `google_credentials.json` is in the `config/` folder
- Check the filename is exactly `google_credentials.json`

### "Token expired" or "Invalid token"
- Delete `config/google_token.json`
- Run JARVIS again - it will prompt for re-authorization

### "Access denied" or "Insufficient permissions"
- Make sure you added both scopes in Step 3
- Try deleting the token and re-authorizing

### "This app isn't verified" warning
- This is normal for personal projects
- Click **Advanced** → **Go to JARVIS (unsafe)**
- This is safe since you created the app yourself

### Browser doesn't open automatically
- Copy the URL from the terminal
- Paste it in your browser manually
- Complete the authorization

---

## Without Google Docs

If you don't want to set up Google Docs, JARVIS can still:
- Search scholarly databases
- Analyze sources
- Generate outlines
- Write content

The paper will be saved as a local Markdown file instead:
```
data/research_papers/[topic]_[date].md
```

You can then copy this into any document editor.

---

## Security Notes

- **google_credentials.json** - Contains your OAuth client ID (not secret, but don't share)
- **google_token.json** - Contains your access token (keep private, don't commit to git)
- Both files are in `.gitignore` by default
- Tokens expire and refresh automatically
- You can revoke access anytime at [Google Account Security](https://myaccount.google.com/permissions)

---

## Quick Reference

| File | Location | Purpose |
|------|----------|---------|
| `google_credentials.json` | `config/` | OAuth client configuration |
| `google_token.json` | `config/` | Your access token (auto-created) |

| Command | Action |
|---------|--------|
| "Check Google Docs setup" | Verify configuration |
| "Write research paper on [topic]" | Create paper in Google Docs |
| "Show my research projects" | List all papers |

---

## Need Help?

If you're still having issues:
1. Check the JARVIS logs in `logs/jarvis.log`
2. Ensure you're using the correct Google account
3. Try the setup process again from Step 4

For more information, see the [Google Docs API documentation](https://developers.google.com/docs/api/quickstart/python).
