# Instagram Account Setup Guide

This system uses **authenticated account rotation** to handle Instagram content, including age-restricted videos. It implements professional rate limiting, session management, and automatic account health monitoring.

## Quick Start

### Step 1: Create Throwaway Instagram Accounts

**Recommended: 3-5 accounts** (More accounts = higher capacity)

For each account:
1. Go to [instagram.com](https://instagram.com)
2. Sign up with a new email
3. Choose username like: `downloader_bot_123`, `api_scraper_456`, etc.
4. **Important:** Complete basic profile setup (add profile pic, bio)
5. **Wait 24-48 hours** before using for scraping (lets account "warm up")

### Step 2: Add Credentials to `.env`

```bash
# First account (required)
INSTAGRAM_USERNAME=your_first_account
INSTAGRAM_PASSWORD=password123

# Second account (optional)
INSTAGRAM_USERNAME_2=your_second_account
INSTAGRAM_PASSWORD_2=password456

# Third account (optional)
INSTAGRAM_USERNAME_3=your_third_account
INSTAGRAM_PASSWORD_3=password789

# Add more as needed (USERNAME_4, USERNAME_5, etc.)
```

### Step 3: Restart Server

```bash
uvicorn main:app --reload
```

The system will automatically:
- ✅ Detect all configured accounts
- ✅ Login and save sessions
- ✅ Rotate between accounts automatically
- ✅ Monitor account health
- ✅ Respect rate limits (180 requests/hour per account)

## How It Works

### Intelligent Account Rotation

```
Request 1 → Account 1 (1/180 requests used)
Request 2 → Account 1 (2/180 requests used)
...
Request 181 → Account 2 (Account 1 quota full, switches to Account 2)
Request 362 → Account 3 (Account 2 quota full, switches to Account 3)
Hour passes → All quotas reset automatically
```

### Session Management

- **First login:** Credentials used, session saved to `instagram_sessions/`
- **Future requests:** Reuses saved session (no re-login needed)
- **Session expires:** Automatically re-authenticates
- Sessions persist across server restarts

### Health Monitoring

Monitor account health via API:

```bash
GET /tools/social/instagram/account-stats
```

**Response:**
```json
{
  "success": true,
  "message": "3/3 accounts healthy",
  "data": {
    "total_accounts": 3,
    "healthy_accounts": 3,
    "accounts": [
      {
        "username": "downloader_bot_123",
        "is_healthy": true,
        "requests_this_hour": 45,
        "total_requests": 1234,
        "quota_remaining": 135,
        "ban_count": 0,
        "last_error": null
      }
    ]
  }
}
```

## Capacity Planning

**Per Account Limits:**
- 180 requests/hour (conservative, Instagram allows ~200)
- 4,320 requests/day per account

**Total Capacity:**
- 1 account = 4,320 requests/day
- 3 accounts = 12,960 requests/day
- 5 accounts = 21,600 requests/day

## Fallback Strategy

The system tries methods in this order:

1. **Instaloader** (fast, no auth) → Works for most public videos
2. **Instagrapi with rotation** (authenticated) → Handles age-restricted content
3. **yt-dlp** (unauthenticated) → Final fallback

## Account Safety

### DO:
✅ Use throwaway/dedicated accounts (not personal)
✅ Complete basic profile setup
✅ Wait 24-48h before heavy usage
✅ Use residential proxies (already configured via IP2WORLD)
✅ Monitor account health regularly

### DON'T:
❌ Use your personal Instagram account
❌ Create 100+ accounts at once (gets flagged)
❌ Share accounts publicly
❌ Skip the "warm up" period
❌ Exceed rate limits

## Troubleshooting

### "Challenge required" Error
- Account needs verification (email/phone)
- Mark as unhealthy automatically, won't be used
- Verify manually via Instagram app

### "Login failed" Error
- Check credentials in `.env`
- Account might be banned/restricted
- Create new account

### "Rate limited" Error
- Normal behavior when quota exhausted
- System automatically switches to next account
- Wait for hourly reset

### All Accounts Unhealthy
- Check `/tools/social/instagram/account-stats`
- Review `last_error` for each account
- May need to create new accounts

## Advanced Configuration

### Custom Rate Limits

Edit `app/services/tools/socials/instagram_account_manager.py`:

```python
MAX_REQUESTS_PER_HOUR = 180  # Adjust as needed
```

### Session Directory

Sessions stored in: `instagram_sessions/`

To force re-login, delete session files:
```bash
rm -rf instagram_sessions/*
```

## Security Notes

⚠️ **NEVER commit these to Git:**
- `.env` file (contains passwords)
- `instagram_sessions/` directory
- `instagram_cookies.txt`

These are already in `.gitignore`

## Support

For issues, check:
1. Server logs for detailed error messages
2. `/tools/social/instagram/account-stats` endpoint
3. Account health in Instagram app

---

**Last Updated:** 2025-12-04
