#!/usr/bin/env python3
"""
SQLite Database Browser Script
This script helps you view tables and data in your local SQLite database.
"""

import sqlite3
import os
import sys
from tabulate import tabulate

def get_db_path():
    """Get the SQLite database path."""
    return "./prepgenie_local.db"

def connect_to_db():
    """Connect to the SQLite database."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("Make sure you've run the backend at least once to create the database.")
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

def view_table_data(conn, table_name, limit=10):
    """View sample data from a table."""
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
        rows = cursor.fetchall()
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        return column_names, rows
    except Exception as e:
        return None, f"Error: {e}"

def main():
    print("🗄️  SQLite Database Browser for PrepGenie")
    print("=" * 50)
    
    # Connect to database
    conn = connect_to_db()
    if not conn:
        return
    
    print(f"✅ Connected to database: {get_db_path()}")
    print()
    
    # List all tables
    tables = list_tables(conn)
    if not tables:
        print("📭 No tables found in the database.")
        print("Run the backend application first to create tables.")
        conn.close()
        return
    
    print(f"📋 Found {len(tables)} table(s):")
    for i, table in enumerate(tables, 1):
        row_count = count_rows(conn, table)
        print(f"  {i}. {table} ({row_count} rows)")
    print()
    
    # Interactive menu
    while True:
        print("Options:")
        print("1. View table schema")
        print("2. View table data")
        print("3. List all tables")
        print("4. Execute custom SQL query")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            print("\nAvailable tables:")
            for i, table in enumerate(tables, 1):
                print(f"  {i}. {table}")
            
            try:
                table_num = int(input("Enter table number: ")) - 1
                if 0 <= table_num < len(tables):
                    table_name = tables[table_num]
                    columns = describe_table(conn, table_name)
                    
                    print(f"\n📊 Schema for table '{table_name}':")
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
                else:
                    print("❌ Invalid table number.")
            except ValueError:
                print("❌ Please enter a valid number.")
                
        elif choice == "2":
            print("\nAvailable tables:")
            for i, table in enumerate(tables, 1):
                print(f"  {i}. {table}")
            
            try:
                table_num = int(input("Enter table number: ")) - 1
                if 0 <= table_num < len(tables):
                    table_name = tables[table_num]
                    limit = input("Enter number of rows to show (default 10): ").strip()
                    limit = int(limit) if limit else 10
                    
                    column_names, rows = view_table_data(conn, table_name, limit)
                    
                    if column_names:
                        print(f"\n📋 Data from table '{table_name}' (showing up to {limit} rows):")
                        if rows:
                            print(tabulate(rows, headers=column_names, tablefmt="grid"))
                        else:
                            print("📭 No data found in this table.")
                    else:
                        print(f"❌ Error viewing table: {rows}")
                else:
                    print("❌ Invalid table number.")
            except ValueError:
                print("❌ Please enter a valid number.")
                
        elif choice == "3":
            print(f"\n📋 All tables:")
            for i, table in enumerate(tables, 1):
                row_count = count_rows(conn, table)
                print(f"  {i}. {table} ({row_count} rows)")
                
        elif choice == "4":
            print("\n⚠️  Custom SQL Query (be careful!):")
            query = input("Enter SQL query: ").strip()
            if query:
                try:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    
                    if query.lower().startswith('select'):
                        rows = cursor.fetchall()
                        if rows:
                            # Try to get column names
                            column_names = [description[0] for description in cursor.description]
                            print(tabulate(rows, headers=column_names, tablefmt="grid"))
                        else:
                            print("📭 No results returned.")
                    else:
                        conn.commit()
                        print("✅ Query executed successfully.")
                        # Refresh tables list
                        tables = list_tables(conn)
                        
                except Exception as e:
                    print(f"❌ Error executing query: {e}")
                    
        elif choice == "5":
            break
            
        else:
            print("❌ Invalid choice. Please enter 1-5.")
        
        print()
    
    conn.close()
    print("👋 Goodbye!")

if __name__ == "__main__":
    main()
