# Railway Deployment Guide

This document explains how to deploy the Workspace AI Assistant backend to Railway.

## Environment Variables

The backend is fully configured to run on Railway without a local `.env` file. You must set the following Environment Variables in your Railway project dashboard.

### `GEMINI_API_KEY`
- **What it is:** Your Google Gemini API Key.
- **Where to get it:** [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Example:** `AIzaSy...`

### `FRONTEND_URL`
- **What it is:** The URL where your Vercel/Netlify frontend is hosted. This is required to properly configure CORS, allowing your frontend to talk to the backend.
- **Example:** `https://workspace-ai.vercel.app`

### `REDIRECT_URI`
- **What it is:** The callback URL Google redirects the user to after they log in. Since the backend handles the OAuth flow, this MUST point to the `/auth/callback` endpoint on your Railway deployment.
- **Example:** `https://workspace-ai-production.up.railway.app/auth/callback`
- **Important:** Ensure you add this exact URL to the "Authorized redirect URIs" list in your Google Cloud Console.

### `GOOGLE_CREDENTIALS_FILE` (Optional)
- **What it is:** The absolute path to your `credentials.json` file inside the deployment container.
- **Default:** `credentials/credentials.json`
- **How to provide it in Railway:** Railway does not natively support uploading files directly to the root. However, you can commit your `credentials.json` (not recommended for public repos), or use a build step that reads a base64 environment variable and decodes it into a file during deployment. 

## Local vs Production

- **Local Development**: Just run `uvicorn backend.app:app --reload`. The backend will use `localhost` defaults and read from `.env` automatically.
- **Railway Production**: The server will seamlessly pick up the Railway variables, overwrite the local defaults, apply CORS for your `FRONTEND_URL`, and log warnings if any critical configuration is missing on startup.

## Missing Credentials Graceful Failure
If `credentials.json` is missing in production, the server will no longer crash. It will start successfully and log a startup warning. If a user attempts to login, the `/login` endpoint will return a clean `500 Server Configuration Error` instead of bringing down the entire application.
