# Deployment Instructions for User Type System

## Overview
This guide covers deploying the new user type system to your VM environment.

## Pre-Migration Steps

1. **Commit and Push Changes**
   ```bash
   # On your local machine
   git add .
   git commit -m "Add user type system with rating functionality"
   git push origin main
   ```

2. **Pull Changes on VM**
   ```bash
   # On your VM
   cd /path/to/your/project
   git pull origin main
   ```

## Database Migration

3. **Stop Flask Application**
   ```bash
   # Stop your current Flask app (method depends on how you're running it)
   # If using systemd:
   sudo systemctl stop your-flask-app
   
   # If using screen/tmux, exit the session
   # If running directly, use Ctrl+C
   ```

4. **Run Database Migration**
   ```bash
   # On your VM, in the project directory
   python migrate_production.py
   ```

   This script will:
   - ✅ Find your database automatically
   - 💾 Create a backup 
   - 🔧 Add the `user_type` column
   - 📊 Create the `ratings` table
   - 🎯 Set users with pseudocodes starting with '9' as proficient
   - 📈 Create necessary indexes

5. **Verify Migration Success**
   The script should output something like:
   ```
   📊 Migration completed successfully!
      📁 Database: instance/pseudocodes.db
      💾 Backup: instance/pseudocodes.db.backup
      👥 Normal users: X
      🎯 Proficient users: Y
      ⭐ Total ratings: 0
   ```

## Test User Creation (Optional)

6. **Create Test Users**
   When prompted by the migration script, choose 'y' to create test users:
   - **Normal Users**: 12345, 67890
   - **Proficient Users**: 90001, 91234

## Restart Application

7. **Start Flask Application**
   ```bash
   # Restart your Flask app using your usual method
   # If using systemd:
   sudo systemctl start your-flask-app
   
   # If running directly:
   python app.py
   
   # If using gunicorn:
   gunicorn -c gunicorn_config.py app:app
   ```

## Verification Steps

8. **Test Normal Users**
   - Login with pseudocode: 12345 or 67890
   - Navigation should show: "Welcome 12345! Normal"
   - Results page should NOT show rating interface

9. **Test Proficient Users**
   - Login with pseudocode: 90001 or 91234  
   - Navigation should show: "Welcome 90001! Proficient"
   - Results page should show rating interface at bottom
   - Try submitting a rating

## Troubleshooting

### If Migration Fails
```bash
# Restore from backup if something goes wrong
cp instance/pseudocodes.db.backup instance/pseudocodes.db
```

### If App Won't Start
1. Check the error logs
2. Verify all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

### If Rating System Doesn't Work
1. Check browser console for JavaScript errors
2. Verify the `/api/submit-rating` endpoint is accessible
3. Check that proficient users can access the rating interface

## Architecture Changes Summary

### New Database Schema
- `pseudocodes.user_type`: 'normal' or 'proficient'
- `ratings` table: stores user feedback from proficient users

### New Features
- **Navigation**: Shows user type badges
- **Rating Interface**: Only visible to proficient users
- **API Endpoint**: `/api/submit-rating` for rating submission

### Backward Compatibility
- All existing users default to 'normal' type
- Existing functionality unchanged for all users
- Rating system is additive (doesn't affect core features)

## File Changes Summary
- ✅ `app/models.py` - Added UserType enum, Rating model, enhanced Pseudocode
- ✅ `app/routes.py` - Added `/api/submit-rating` endpoint
- ✅ `app/templates/base.html` - Enhanced navigation with user type display
- ✅ `app/templates/result.html` - Added rating interface for proficient users
- ✅ `migrate_production.py` - Production-safe migration script
- ✅ `USER_TYPE_SYSTEM.md` - Comprehensive documentation
- ✅ `CLAUDE.md` - Updated project documentation

## Success Indicators

✅ **Migration Successful**: Script completes without errors  
✅ **App Starts**: Flask application runs without database errors  
✅ **Normal Users Work**: Can login and use system normally  
✅ **Proficient Users Work**: Can login and see rating interface  
✅ **Ratings Submit**: Proficient users can successfully submit ratings  

If all indicators are green, deployment is successful! 🎉