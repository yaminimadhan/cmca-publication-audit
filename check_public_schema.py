#!/usr/bin/env python3
"""
Check what's in the public schema before deletion
"""

import os
import psycopg2

# Set environment variable
os.environ['DATABASE_URL'] = 'postgresql://postgres:password@localhost:5432/postgres'

def check_public_schema():
    """Check what tables are in the public schema"""
    print("🔍 Checking Public Schema Contents")
    print("=" * 50)
    
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        
        # Get all tables in public schema (excluding system tables)
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name NOT LIKE 'pg_%'
            ORDER BY table_name;
        """)
        
        tables = [row[0] for row in cur.fetchall()]
        
        print(f"📊 Found {len(tables)} tables in public schema:")
        print("-" * 30)
        
        if tables:
            for table in tables:
                try:
                    # Get row count for each table (handle case sensitivity)
                    cur.execute(f'SELECT COUNT(*) FROM public."{table}";')
                    count = cur.fetchone()[0]
                    print(f"  📄 {table} ({count:,} rows)")
                except Exception as e:
                    print(f"  📄 {table} (error counting: {str(e)[:50]}...)")
        else:
            print("  ✅ No user tables found in public schema")
        
        # Check if capstone_vector schema exists
        cur.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = 'capstone_vector';
        """)
        
        capstone_exists = cur.fetchone() is not None
        
        print(f"\n📁 capstone_vector schema: {'✅ EXISTS' if capstone_exists else '❌ NOT FOUND'}")
        
        if capstone_exists:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'capstone_vector'
                ORDER BY table_name;
            """)
            
            capstone_tables = [row[0] for row in cur.fetchall()]
            print(f"  📊 capstone_vector tables: {capstone_tables}")
        
        conn.close()
        
        return tables
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == "__main__":
    tables = check_public_schema()
    
    if tables:
        print(f"\n⚠️  WARNING: {len(tables)} tables will be DELETED!")
        print("\nThese appear to be your old assignment tables.")
        print("Make sure you have backups if you need this data.")
    else:
        print("\n✅ Public schema is clean - no user tables to delete.")
