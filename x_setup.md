
# Steps to Get X Client ID and Secret

1.  **Go to Developer Portal**: Log in to the [X Developer Portal](https://developer.x.com).
2.  **Create Project/App**:
    - Create a new **Project** if you haven't.
    - Inside it, create a new **App**.
3.  **Setup User Authentication**:
    - Go to your App Settings -> **User authentication settings** -> **Edit**.
    - **App permissions**: Select "Read and write".
    - **Request email from users**: **CHECK THIS BOX**. (Supabase requires an email to create a user).
    - **Type of App**: Select "Web App, Automated App or Bot".
    - **App Info**:
        - **Callback URI / Redirect URL**: Copy this from Supabase (Authentication -> Providers -> Twitter -> Callback URL). 
          **CRITICAL**: It should look like `https://wkddcjtdhdjvuayjzwmb.supabase.co/auth/v1/callback`.
        - **Website URL**: usage `https://wkddcjtdhdjvuayjzwmb.supabase.co` (Your Supabase Project URL). 
          *Note: Do NOT put the callback URL here. This is just the "Homepage" of your app.*
    - Click **Save**.
4.  **Get Keys**:
    - Go to **Keys and Tokens** tab.
    - Look for **OAuth 2.0 Client ID and Client Secret**.
    - If empty, click **Regenerate**.
    - **Copy these** immediately (you won't see the secret again).
5.  **Configure Supabase**:
    - Go to Supabase -> Authentication -> Providers -> Twitter.
    - Paste the **Client ID** and **Client Secret**.
    - Turn **Enabled** to ON.
