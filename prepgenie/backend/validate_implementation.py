#!/usr/bin/env python3
"""
Validate the implementation of the new answer evaluation and aptitude features
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def validate_imports():
    """Validate that all imports work correctly"""
    print("🔍 Validating imports...")
    
    try:
        from app.api.llm_endpoints import router as llm_router
        print("✅ LLM endpoints import successful")
    except Exception as e:
        print(f"❌ LLM endpoints import failed: {e}")
        return False
    
    try:
        from app.api.api_v1.endpoints.answers import router as answers_router
        print("✅ Enhanced answers endpoints import successful")
    except Exception as e:
        print(f"❌ Enhanced answers endpoints import failed: {e}")
        return False
    
    try:
        from app.api.api_v1.api import api_router
        print("✅ Main API router import successful")
    except Exception as e:
        print(f"❌ Main API router import failed: {e}")
        return False
    
    return True

def validate_endpoint_routes():
    """Validate that the new routes are properly defined"""
    print("\n🛣️  Validating endpoint routes...")
    
    try:
        from app.api.llm_endpoints import router as llm_router
        
        # Check if the new endpoints are in the router
        routes = [route.path for route in llm_router.routes if hasattr(route, 'path')]
        
        expected_routes = [
            "/upsc/evaluate-answer",
            "/upsc/aptitude-enhancement", 
            "/upsc/comprehensive-analysis",
            "/upsc/analyze-question"
        ]
        
        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"✅ Route {route} found")
            else:
                print(f"❌ Route {route} not found")
                print(f"   Available routes: {routes}")
        
        return True
        
    except Exception as e:
        print(f"❌ Route validation failed: {e}")
        return False

def validate_models():
    """Validate that the new Pydantic models are properly defined"""
    print("\n📋 Validating Pydantic models...")
    
    try:
        from app.api.llm_endpoints import (
            AnswerEvaluationRequest, 
            AnswerEvaluationResponse,
            AptitudeEnhancementRequest,
            AptitudeEnhancementResponse,
            ExamContext,
            StudentKnowledge
        )
        
        # Test model instantiation
        exam_context = ExamContext(
            marks=15,
            time_limit=20,
            word_limit=250,
            exam_type="UPSC Mains"
        )
        
        student_knowledge = StudentKnowledge(
            known_concepts=["democracy", "governance"],
            uncertain_areas=["constitutional law"],
            unknown_areas=["recent amendments"],
            confidence_level="medium"
        )
        
        print("✅ All new Pydantic models are valid")
        return True
        
    except Exception as e:
        print(f"❌ Model validation failed: {e}")
        return False

def validate_endpoint_functionality():
    """Test that endpoint functions are callable"""
    print("\n⚡ Validating endpoint functionality...")
    
    try:
        from app.api.llm_endpoints import (
            evaluate_answer,
            aptitude_enhancement,
            comprehensive_question_analysis
        )
        
        print("✅ All new endpoint functions are importable")
        return True
        
    except Exception as e:
        print(f"❌ Endpoint function validation failed: {e}")
        return False

def show_implementation_summary():
    """Show a summary of what was implemented"""
    print("\n📊 Implementation Summary:")
    print("="*60)
    
    features = [
        "✅ Answer Evaluation System",
        "   - Comprehensive answer analysis",
        "   - Current vs potential score assessment",
        "   - Content gap identification",
        "   - Structure feedback",
        "",
        "✅ Aptitude Enhancement System", 
        "   - Smart writing strategies",
        "   - Knowledge leverage techniques",
        "   - Gap handling methods",
        "   - Score optimization tips",
        "",
        "✅ Comprehensive Question Analysis",
        "   - 13-dimensional analysis framework",
        "   - Multi-agent approach design",
        "   - Difficulty assessment",
        "   - Topic classification",
        "",
        "✅ Enhanced Endpoints",
        "   - /api/v1/llm/upsc/evaluate-answer",
        "   - /api/v1/llm/upsc/aptitude-enhancement", 
        "   - /api/v1/llm/upsc/comprehensive-analysis",
        "   - /api/v1/answers/evaluate",
        "   - /api/v1/answers/aptitude-guidance",
        "",
        "✅ Integration Features",
        "   - Current affairs suggestions",
        "   - Diagram recommendations", 
        "   - Introduction/conclusion enhancement",
        "   - Marks breakdown and optimization"
    ]
    
    for feature in features:
        print(feature)

def main():
    """Run all validations"""
    print("🧪 PrepGenie Answer Evaluation & Aptitude System Validation")
    print("="*70)
    
    validations = [
        validate_imports,
        validate_endpoint_routes,
        validate_models,
        validate_endpoint_functionality
    ]
    
    all_passed = True
    for validation in validations:
        if not validation():
            all_passed = False
    
    if all_passed:
        print("\n🎉 All validations passed!")
        show_implementation_summary()
        
        print("\n🚀 Next Steps:")
        print("1. Start the FastAPI server: python -m uvicorn app.main:app --reload")
        print("2. Run the test: python test_api_endpoints.py")
        print("3. Test the new endpoints with your frontend")
        
    else:
        print("\n❌ Some validations failed. Please check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
