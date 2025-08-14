#!/usr/bin/env python3
"""
Simple test to check if AI generation is working properly.
"""

import os
import sys
import asyncio

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["GEMINI_API_KEY"] = "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos"
os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"

async def test_ai_generation():
    """Test basic AI generation."""
    
    from app.services.ai_factory import get_ai_provider
    
    print("Testing AI Provider...")
    
    ai_provider = get_ai_provider()
    print(f"✅ AI Provider initialized: {ai_provider.get_model_name()}")
    
    # Test text generation
    print("\n1. Testing text generation...")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello World' and nothing else."}
    ]
    
    response = await ai_provider.generate_response(messages)
    print(f"Response: {response}")
    
    # Test JSON generation
    print("\n2. Testing JSON generation...")
    messages = [
        {"role": "system", "content": "You are a JSON generator. Return only valid JSON."},
        {"role": "user", "content": 'Return this JSON: {"test": "working", "status": "ok"}'}
    ]
    
    json_response = await ai_provider.generate_json_response(messages)
    print(f"JSON Response: {json_response}")
    
    # Test question generation
    print("\n3. Testing question generation...")
    from app.services.ai_question_agent import AIQuestionAgent
    
    agent = AIQuestionAgent()
    questions = await agent.generate_questions(
        "Preciso de um sistema para controlar estoque de uma loja de roupas",
        num_questions=3
    )
    
    print(f"Generated {len(questions)} questions:")
    for q in questions:
        print(f"  - {q.text}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_ai_generation())