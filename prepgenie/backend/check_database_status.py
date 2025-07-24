#!/usr/bin/env python3
"""
Direct database check for Shakti's PDF processing status
"""

import sqlite3
import json
from pathlib import Path

def check_database_status():
    """Check the database directly for processing status"""
    db_path = Path("prepgenie_local.db")
    
    if not db_path.exists():
        print("❌ Database not found")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check answers table
        cursor.execute("""
            SELECT id, question_id, file_path, evaluation, created_at 
            FROM answers 
            ORDER BY id DESC 
            LIMIT 5
        """)
        
        answers = cursor.fetchall()
        print(f"📊 Recent answers in database: {len(answers)}")
        
        for answer in answers:
            answer_id, question_id, file_path, evaluation, created_at = answer
            print(f"\n📄 Answer ID: {answer_id}")
            print(f"   Question ID: {question_id}")
            print(f"   File: {file_path}")
            print(f"   Created: {created_at}")
            
            if evaluation:
                try:
                    eval_data = json.loads(evaluation)
                    print(f"   ✅ Evaluation exists: {len(eval_data.keys())} keys")
                    
                    # Show key components
                    if 'score' in eval_data:
                        print(f"      Score: {eval_data['score']}")
                    if 'feedback' in eval_data:
                        feedback_len = len(str(eval_data['feedback']))
                        print(f"      Feedback: {feedback_len} chars")
                    if 'comprehensive_analysis' in eval_data:
                        analysis = eval_data['comprehensive_analysis']
                        print(f"      Analysis: {len(analysis.keys())} dimensions")
                        
                except json.JSONDecodeError:
                    print(f"   ⚠️  Evaluation data corrupted")
            else:
                print(f"   ⏳ No evaluation yet")
        
        # Check progress tracking table if exists
        try:
            cursor.execute("""
                SELECT answer_id, step, status, progress, message, updated_at
                FROM progress_tracking 
                WHERE answer_id = (SELECT MAX(id) FROM answers)
                ORDER BY updated_at DESC
                LIMIT 10
            """)
            
            progress_records = cursor.fetchall()
            if progress_records:
                print(f"\n📈 Progress tracking records: {len(progress_records)}")
                for record in progress_records[:5]:  # Show latest 5
                    answer_id, step, status, progress, message, updated_at = record
                    print(f"   {updated_at}: {step} - {status} ({progress}%)")
                    if message:
                        print(f"      Message: {message[:100]}...")
            else:
                print(f"\n📈 No progress tracking records found")
                
        except sqlite3.OperationalError:
            print(f"\n📈 Progress tracking table doesn't exist")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    print("🗃️  Checking Database Status for Shakti's PDF...")
    check_database_status()
