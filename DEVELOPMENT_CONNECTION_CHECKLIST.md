# Development Connection Troubleshooting Checklist

## Issue: Frontend not connecting to local backend

### Quick Checks:

1. **Backend is running**
   ```bash
   cd backend_app
   python main.py
   ```
   Should show: `Uvicorn running on http://0.0.0.0:8000`

2. **Check your laptop's IP address**
   ```powershell
   ipconfig | Select-String -Pattern "IPv4"
   ```
   Current IP: **10.63.60.207**

3. **Update frontend config if IP changed**
   Edit `frontend_app/lib/core/config.dart`:
   ```dart
   static const String _realDeviceUrl = "http://10.63.60.207:8000";
   ```

4. **Phone and laptop on same network**
   - Both must be on the same WiFi network
   - Or phone connected via USB with USB debugging enabled

5. **Test backend from laptop browser**
   Open: http://localhost:8000/health
   Should return: `{"status":"ok","database_configured":true}`

6. **Test backend from phone browser**
   Open: http://10.63.60.207:8000/health
   Should return same as above

7. **Firewall check**
   Windows Firewall might block port 8000:
   ```powershell
   # Allow port 8000
   netsh advfirewall firewall add rule name="FastAPI Dev" dir=in action=allow protocol=TCP localport=8000
   ```

8. **Hot restart Flutter app**
   After changing config.dart:
   - Press `r` in terminal where `flutter run` is running
   - Or: Stop and restart the app

## Common Issues:

### "Connection refused" or "Network unreachable"
- IP address changed (run `ipconfig` and update config.dart)
- Backend not running
- Phone not on same network

### "Backend disabled" message in app
- Config still pointing to old IP
- Firewall blocking connection
- Backend crashed (check terminal for errors)

### Backend starts but crashes immediately
- Check .env file has all required API keys
- Check database connection in .env
- Run: `cd backend_app && python check_env.py`

## Current Configuration:

**Backend**: Running on `0.0.0.0:8000` (accessible from network)
**Frontend Config**: `http://10.63.60.207:8000`
**Network**: WiFi (IP changes when reconnecting)

## Quick Fix Steps:

1. Get current IP: `ipconfig | Select-String -Pattern "IPv4"`
2. Update `frontend_app/lib/core/config.dart` with new IP
3. Hot restart Flutter app (press `r` or restart)
4. Test in browser: `http://YOUR_IP:8000/health`
