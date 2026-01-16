from nicegui import app, ui
from database import get_client
import database

import os

# Define the callback URL (adjust for production if needed)
# For local dev: http://localhost:8080/auth/callback

def get_site_url():
    url = os.environ.get('SITE_URL', 'http://localhost:8080').strip().strip('"').strip("'")
    if not url.startswith('http'):
        url = f"https://{url}"
    return url.rstrip('/')

CALLBACK_URL = f"{get_site_url()}/auth/callback"

def login_with_google():
    """Initiates the Google OAuth flow."""
    # Use global client for initiating auth
    client = get_client()
    if not client:
        ui.notify("Database connection missing!", type='negative')
        return



    data = client.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {
            "redirect_to": CALLBACK_URL,
            "queryParams": {
                "prompt": "select_account"
            }
        }
    })
    
    if data and data.url:
        ui.navigate.to(data.url)
    else:
        ui.notify("Could not start Google Login", type='negative')

def login_with_twitter():
    """Initiates the Twitter OAuth flow."""
    client = get_client()
    if not client:
        ui.notify("Database connection missing!", type='negative')
        return

    data = client.auth.sign_in_with_oauth({
        "provider": "x",
        "options": {
            "redirect_to": CALLBACK_URL
        }
    })
    
    if data and data.url:
        ui.navigate.to(data.url)
    else:
        ui.notify("Could not start Twitter Login", type='negative')

def sign_up_with_email(email, password, full_name, username):
    """Signs up a new user with email and password."""
    client = get_client()
    if not client:
        return None, "Database error"
    try:
        print(f"DEBUG: Signing up with redirect_to: {CALLBACK_URL}")
        res = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name,
                    "username": username
                },
                "email_redirect_to": CALLBACK_URL
            }
        })
        print(f"DEBUG: Signup Result User: {res.user}")
        
        # If Auto-Confirm is enabled in Supabase, we get a session immediately.
        if res.session:
            app.storage.user['user'] = {
                'id': res.user.id,
                'email': res.user.email,
                'metadata': res.user.user_metadata
            }
            # Ensure profile exists and is up to date
            try:
                token = res.session.access_token
                profile = database.get_profile(res.user.id, access_token=token)
                if not profile:
                   database.create_profile(res.user.id, res.user.user_metadata, email=res.user.email, access_token=token)
                else:
                   # Sync username if it's missing or different (Trigger might not have caught it)
                   database.update_profile(res.user.id, {
                       "username": res.user.user_metadata.get('username'),
                       "full_name": res.user.user_metadata.get('full_name'),
                       "email": res.user.email
                   }, access_token=token)
                   print(f"DEBUG: Synced profile for {res.user.email}")
            except Exception as e:
                print(f"DEBUG: Profile sync failed: {e}")
                pass
            return res.user, True # True indicates "Logged In"

        if res.user:
            return res.user, False # False indicates "Check Email"
            
        return None, "Signup failed"
    except Exception as e:
        return None, str(e)

def sign_in_with_email(email, password):
    """Signs in a user with email and password."""
    client = get_client()
    if not client:
        return None, "Database error"
    try:
        res = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if res.user:
            # Store in session immediately
            app.storage.user['user'] = {
                'id': res.user.id,
                'email': res.user.email,
                'metadata': res.user.user_metadata,
                'access_token': res.session.access_token
            }
            # Ensure profile check happens here too
            try:
                token = res.session.access_token
                profile = database.get_profile(res.user.id, access_token=token)
                if not profile:
                   database.create_profile(res.user.id, res.user.user_metadata, email=res.user.email, access_token=token)
                elif profile.get('avatar_url'):
                   app.storage.user['user']['avatar_url'] = profile.get('avatar_url')
            except:
                pass
                
            return res.user, None
        return None, "Login failed"
    except Exception as e:
        return None, str(e)

def logout():
    """Logs out the current user."""
    client = get_client()
    if client:
        try:
             client.auth.sign_out()
        except:
             pass
    app.storage.user.clear() # Clear all session data including referrer_path
    ui.navigate.to('/')

def get_current_user():
    """
    Retrieves the current user from the session. 
    Refreshes the session if needed.
    """
    # 1. Check local session storage first (fast)
    if 'user' in app.storage.user:
        return app.storage.user['user']
    
    # 2. If not in storage, check Supabase via access token if we had one
    # Note: NiceGUI's app.storage.user is the best place to keep persistence 
    # across page reloads for the same browser session.
    
    return None

def handle_auth_callback(code: str):
    """
    Exchanges the auth code for a session.
    Expected to be called on the /auth/callback page.
    """
    client = get_client()
    if not client:
        return False

    try:
        # Exchange code for session
        res = client.auth.exchange_code_for_session({
            "auth_code": code
        })
        user = res.user
        
        # Store user info in NiceGUI session
        app.storage.user['user'] = {
            'id': user.id,
            'email': user.email,
            'metadata': user.user_metadata,
            'access_token': res.session.access_token
        }
        
        # Ensure profile exists (in case trigger failed or missing)
        # Ensure profile exists (in case trigger failed or missing)
        try:
            token = res.session.access_token
            profile = database.get_profile(user.id, access_token=token)
            # Try to grab X handle if available (usually 'user_name' in metadata for Twitter)
            x_handle = user.user_metadata.get('user_name') if user.app_metadata.get('provider') in ('twitter', 'x') else None
            
            if not profile:
                database.create_profile(user.id, user.user_metadata, email=user.email, access_token=token)
                if x_handle:
                     database.update_profile(user.id, {'x_handle': x_handle}, access_token=token)
            else:
                 # Update session with DB avatar
                 if profile.get('avatar_url'):
                     app.storage.user['user']['avatar_url'] = profile['avatar_url']
                   
                 if x_handle and not profile.get('x_handle'):
                     # Link X handle if not already set
                     database.update_profile(user.id, {'x_handle': x_handle}, access_token=token)

        except Exception as e:
            print(f"Profile check failed: {e}")

        return True
    except Exception as e:
        print(f"Auth Error: {e}")
        return False
