#!/usr/bin/env python3
"""
Simple Supabase Connection Fix for GSSAPI Issues
This script provides specific solutions for the GSSAPI negotiation error.
"""

import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

def test_supabase_connection_fixes():
    """Test different connection methods to fix GSSAPI issues"""
    
    user = os.getenv("user")
    password = os.getenv("password") 
    host = os.getenv("host")
    port = os.getenv("port", "5432")
    dbname = os.getenv("dbname")
    
    print("🔧 Supabase GSSAPI Connection Fix")
    print("=" * 50)
    print(f"Connecting to: {host}:{port}")
    print(f"Database: {dbname}")
    print(f"User: {user}")
    print()
    
    # Fix 1: Explicit SSL with no GSSAPI
    print("✅ Fix 1: SSL Required + No GSSAPI")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            sslmode='require',
            gssencmode='disable',  # Disable GSSAPI encryption
            connect_timeout=15,
            options='-c gss_enc_mode=disable'  # Alternative way to disable GSSAPI
        )
        
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"   ✅ SUCCESS! Connected with SSL, no GSSAPI")
            print(f"   📊 PostgreSQL: {version.split(',')[0]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Fix 2: Connection string with explicit parameters
    print("\n✅ Fix 2: Connection String with GSSAPI Disabled")
    try:
        encoded_password = quote_plus(password)
        connection_string = (
            f"postgresql://{user}:{encoded_password}@{host}:{port}/{dbname}"
            f"?sslmode=require&gssencmode=disable&application_name=PrepGenie"
        )
        
        conn = psycopg2.connect(connection_string, connect_timeout=15)
        
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user;")
            db, current_user = cur.fetchone()
            print(f"   ✅ SUCCESS! Connected via connection string")
            print(f"   📁 Database: {db}")
            print(f"   👤 User: {current_user}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Fix 3: Minimal connection (prefer SSL)
    print("\n✅ Fix 3: Minimal Connection (SSL Prefer)")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            sslmode='prefer',
            connect_timeout=20
        )
        
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            print(f"   ✅ SUCCESS! Minimal connection worked")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Fix 4: No SSL (last resort)
    print("\n✅ Fix 4: No SSL (Last Resort)")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            sslmode='disable',
            connect_timeout=20
        )
        
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            print(f"   ⚠️  SUCCESS but NO SSL! (Not recommended for production)")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    return False

def create_database_url_with_fix():
    """Generate the correct DATABASE_URL for your config.py"""
    
    user = os.getenv("user")
    password = os.getenv("password")
    host = os.getenv("host") 
    port = os.getenv("port", "5432")
    dbname = os.getenv("dbname")
    
    encoded_password = quote_plus(password)
    
    # Recommended DATABASE_URL for Supabase
    database_url = (
        f"postgresql://{user}:{encoded_password}@{host}:{port}/{dbname}"
        f"?sslmode=require&gssencmode=disable"
    )
    
    print("\n🔗 Recommended DATABASE_URL Configuration")
    print("=" * 50)
    print("Add this to your config.py or .env:")
    print()
    print(f'DATABASE_URL="{database_url}"')
    print()
    print("Or update your config.py to include gssencmode=disable:")
    print("""
# In config.py, update your DATABASE_URL construction:
encoded_password = quote_plus(self.DB_PASSWORD)
self.DATABASE_URL = (
    f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:"
    f"{self.DB_PORT}/{self.DB_NAME}?sslmode=require&gssencmode=disable"
)
""")

def update_config_file():
    """Update the config.py file with GSSAPI fix"""
    config_path = "/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/backend/app/core/config.py"
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Check if already has gssencmode
        if 'gssencmode=disable' in content:
            print("✅ config.py already has GSSAPI fix")
            return True
        
        # Find and replace the DATABASE_URL construction
        old_pattern = 'f"{self.DB_PORT}/{self.DB_NAME}?sslmode=require"'
        new_pattern = 'f"{self.DB_PORT}/{self.DB_NAME}?sslmode=require&gssencmode=disable"'
        
        if old_pattern in content:
            updated_content = content.replace(old_pattern, new_pattern)
            
            with open(config_path, 'w') as f:
                f.write(updated_content)
            
            print("✅ Updated config.py with GSSAPI fix")
            print("   Added gssencmode=disable to DATABASE_URL")
            return True
        else:
            print("⚠️  Could not automatically update config.py")
            print("   Please manually add '&gssencmode=disable' to your DATABASE_URL")
            return False
            
    except Exception as e:
        print(f"❌ Error updating config.py: {e}")
        return False

def main():
    print("🚀 PrepGenie Supabase GSSAPI Fix Tool")
    print("=" * 50)
    
    # Test connections
    if test_supabase_connection_fixes():
        print("\n🎉 SUCCESS! Found a working connection method.")
        
        # Update config if needed
        print("\n🔧 Updating configuration files...")
        update_config_file()
        
        print("\n✅ Next steps:")
        print("1. Restart your FastAPI server")
        print("2. Test the /auth/health endpoint")
        print("3. Try registration/login in your frontend")
        
    else:
        print("\n❌ All connection methods failed.")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check your Supabase project is active")
        print("2. Verify your IP is allowlisted in Supabase settings")
        print("3. Check if your credentials are correct")
        print("4. Try deploying to Railway/Vercel for better connectivity")
    
    # Always show the recommended configuration
    create_database_url_with_fix()

if __name__ == "__main__":
    main()
