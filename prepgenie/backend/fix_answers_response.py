#!/usr/bin/env python3
"""
Fix the answers.py file to have the correct AnswerUploadResponse format
"""

# Read the file
with open('app/api/api_v1/endpoints/answers.py', 'r') as f:
    content = f.read()

# Replace the problematic return statement
old_return = '''        return AnswerUploadResponse(
            id=answer.id,
            message="Answer uploaded successfully" + (" and processing started" if file_path else ""),
            file_path=file_path
        )'''

new_return = '''        return AnswerUploadResponse(
            id=answer.id,
            message="Answer uploaded successfully" + (" and processing started" if file_path else ""),
            answer=AnswerResponse(
                id=answer.id,
                question_id=answer.question_id,
                content=answer.content,
                file_path=answer.file_path,
                file_name=file.filename if file else None,
                uploaded_at=answer.uploaded_at.isoformat(),
                evaluation=None
            )
        )'''

# Replace
new_content = content.replace(old_return, new_return)

# Write back
with open('app/api/api_v1/endpoints/answers.py', 'w') as f:
    f.write(new_content)

print("✅ Fixed the AnswerUploadResponse format")
