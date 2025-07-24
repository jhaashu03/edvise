#!/usr/bin/env python3
"""
Quick script to view all table schemas in the SQLite database
"""

import sqlite3
import os
from tabulate import tabulate

def get_db_path():
    """Get the SQLite database path."""
    return "./prepgenie_local.db"

def connect_to_db():
    """Connect to the SQLite database."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return None

def list_tables(conn):
    """List all tables in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    return [table[0] for table in tables]

def describe_table(conn, table_name):
    """Get table schema information."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    return columns

def count_rows(conn, table_name):
    """Count rows in a table."""
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        return cursor.fetchone()[0]
    except Exception as e:
        return f"Error: {e}"

def main():
    print("🗄️  PrepGenie SQLite Database Schema Overview")
    print("=" * 60)
    
    # Connect to database
    conn = connect_to_db()
    if not conn:
        return
    
    print(f"✅ Connected to database: {get_db_path()}\n")
    
    # List all tables
    tables = list_tables(conn)
    if not tables:
        print("📭 No tables found in the database.")
        conn.close()
        return
    
    print(f"📋 Database contains {len(tables)} table(s):\n")
    
    # Show schema for each table
    for table_name in tables:
        row_count = count_rows(conn, table_name)
        print(f"🏷️  Table: {table_name} ({row_count} rows)")
        print("-" * 50)
        
        columns = describe_table(conn, table_name)
        headers = ["Column", "Type", "Not Null", "Default", "Primary Key"]
        table_data = []
        
        for col in columns:
            table_data.append([
                col[1],  # name
                col[2],  # type
                "YES" if col[3] else "NO",  # not null
                col[4] if col[4] else "",  # default
                "YES" if col[5] else "NO"   # primary key
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print()
    
    conn.close()
    print("✅ Schema overview complete!")

if __name__ == "__main__":
    main()
