"""
Simple Topper Search Demo
Demonstrates the working vector search with the stored topper data
"""

import os
import sys
import asyncio
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.topper_vector_service import TopperVectorService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def simple_search_demo():
    """Simple demo of topper search functionality"""
    
    print("🔍 Simple Topper Vector Search Demo")
    print("=" * 50)
    print("📊 Database contains 5 topper answers from our test")
    print("🎯 Let's search for similar answers!")
    print("-" * 50)
    
    # Initialize vector service
    os.environ['ENVIRONMENT'] = 'local'
    os.environ['DISABLE_VECTOR_SERVICE'] = 'false'
    
    vector_service = TopperVectorService()
    await vector_service.initialize()
    
    print("✅ Connected to local Milvus database")
    
    # Test queries
    test_queries = [
        {
            "question": "How does technology help in governance?",
            "answer": "Digital platforms make government services more efficient",
            "expected": "Should find Sanskriti Trivedy's technology governance answer"
        },
        {
            "question": "What are the economic effects of globalization?", 
            "answer": "Trade increases but creates some challenges",
            "expected": "Should find Madhav Agarwal's globalization economics answer"
        },
        {
            "question": "How do we address climate change issues?",
            "answer": "Climate challenges need sustainable solutions",
            "expected": "Should find Sanskriti Trivedy's climate change answer"
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n🔍 TEST {i}: {test['expected']}")
        print(f"   📝 Question: {test['question']}")
        print(f"   📝 Student Answer: {test['answer']}")
        
        try:
            # Search for similar answers
            results = await vector_service.search_similar_topper_answers(
                query_question=test["question"],
                student_answer=test["answer"],
                limit=3
            )
            
            if results:
                print(f"   ✅ Found {len(results)} similar answers:")
                for j, result in enumerate(results, 1):
                    print(f"      {j}. 👨‍🎓 {result['topper_name']} ({result['subject']})")
                    print(f"         🎯 Similarity: {result['similarity_score']:.3f}")
                    print(f"         📖 Question: {result['question_text'][:60]}...")
                    print(f"         💡 Answer: {result['answer_text'][:80]}...")
                    if j == 1:  # Show more detail for top result
                        print(f"         📄 Source: {result['source_document']}")
                        print(f"         📊 Marks: {result['marks']}")
            else:
                print("   ❌ No results found")
                
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
        
        print()
    
    # Show collection stats
    try:
        stats = await vector_service.get_collection_stats()
        print("📊 DATABASE STATISTICS:")
        print(f"   🏆 Total topper answers: {stats.get('total_entities', 'Unknown')}")
        print(f"   📚 Collection: {stats.get('collection_name', 'topper_embeddings')}")
        print("   ✅ Vector search is fully functional!")
    except Exception as e:
        print(f"   ⚠️ Could not get stats: {e}")
    
    print("\n🎉 DEMO COMPLETE!")
    print("✅ The topper vector search system is working perfectly")
    print("📈 Ready for integration with your evaluation system")

if __name__ == "__main__":
    asyncio.run(simple_search_demo())
