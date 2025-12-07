# Supabase Setup Guide for JV Directory

## Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up/login
2. Click "New Project"
3. Enter project details:
   - **Name**: `jv-directory`
   - **Database Password**: (save this securely!)
   - **Region**: Choose closest to your users
4. Click "Create new project" and wait for setup (~2 minutes)

## Step 2: Get Your API Keys

1. In your Supabase dashboard, go to **Settings** > **API**
2. Copy these values (you'll need them for `.env`):
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: `eyJhbGc...` (safe for client-side)
   - **service_role key**: `eyJhbGc...` (keep secret! server-side only)

## Step 3: Run the Database Schema

1. In Supabase dashboard, go to **SQL Editor**
2. Click "New query"
3. Copy the contents of `schema.sql` and paste it
4. Click "Run" (or press Cmd+Enter)
5. You should see "Success" for all statements

## Step 4: Configure Authentication

1. Go to **Authentication** > **Providers**
2. Email is enabled by default
3. (Optional) Enable additional providers:
   - Google OAuth
   - GitHub OAuth
   - Magic Link

### Email Templates (Optional)
1. Go to **Authentication** > **Email Templates**
2. Customize confirmation and password reset emails

## Step 5: Set Up Environment Variables

Create a `.env` file in your project root:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-role-key-here

# Optional: For local development
STREAMLIT_SERVER_PORT=8501
```

## Step 6: Install Python Dependencies

```bash
pip install supabase streamlit python-dotenv pandas
```

Or add to `requirements.txt`:
```
streamlit>=1.28.0
supabase>=2.0.0
python-dotenv>=1.0.0
pandas>=2.0.0
```

## Step 7: Import Existing Data

After setup, use the app's "Import CSV" feature to import your `jvdirectory_combined.csv` file.

---

## Database Structure Overview

### Tables

| Table | Purpose |
|-------|---------|
| `profiles` | User accounts (linked to Supabase Auth) |
| `contacts` | Main JV Directory entries |
| `business_categories` | Business focus categories |
| `service_types` | Service provider types |
| `favorites` | User's saved contacts |
| `interactions` | Contact interaction history |
| `import_history` | CSV import tracking |

### User Roles

| Role | Permissions |
|------|------------|
| `admin` | Full access: create, read, update, delete contacts |
| `member` | Read contacts, manage own favorites/interactions |
| `viewer` | Read-only access to contacts |

### Row Level Security (RLS)

All tables have RLS enabled:
- Authenticated users can read contacts
- Only admins can modify contacts
- Users can only access their own favorites/interactions

---

## Troubleshooting

### "Permission denied" errors
- Check that RLS policies are correctly applied
- Verify user has correct role in `profiles` table

### Authentication not working
- Verify SUPABASE_URL and SUPABASE_ANON_KEY are correct
- Check that email provider is enabled in Supabase

### Import failing
- Ensure CSV columns match expected format
- Check for special characters in data

---

## Security Best Practices

1. **Never expose `service_role` key** in client-side code
2. **Use environment variables** for all secrets
3. **Enable RLS** on all tables (already done in schema)
4. **Regularly rotate** database passwords
5. **Monitor** Supabase dashboard for unusual activity
