#!/usr/bin/env python3
"""
Test script for the new 4-API workflow.
Tests all four APIs in sequence to validate the complete flow.
"""

import os
import json
import requests
import sys
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8001"
API_KEY = "test_demandei_key_123"

# Headers for all requests
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_api_1_project_analysis():
    """Test API 1: Project Analysis"""
    print("🔄 Testing API 1: Project Analysis")
    
    payload = {
        "project_description": """
        Preciso desenvolver um sistema web para gestão de clínica médica com 3 médicos e cerca de 200 pacientes por mês.
        
        Funcionalidades principais:
        - Agendamento de consultas online
        - Prontuários eletrônicos
        - Receitas digitais
        - Dashboard para gestão
        - Integração com WhatsApp para lembretes
        
        Orçamento: R$ 80.000
        Prazo: 4 meses
        Preferência por tecnologias modernas e fáceis de manter.
        """,
        "metadata": {
            "user": {"id": "test_user", "platform": "demandei"}
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/project/analyze",
            headers=HEADERS,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API 1 Success!")
            print(f"   Session ID: {data['session_id']}")
            print(f"   Questions generated: {data['total_questions']}")
            print(f"   Project type: {data['project_classification']['type']}")
            return data
        else:
            print(f"❌ API 1 Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ API 1 Error: {str(e)}")
        return None

def test_api_2_questions_response(session_id: str):
    """Test API 2: Questions Response"""
    print("\n🔄 Testing API 2: Questions Response")
    
    # Simulate answering the first batch of questions
    payload = {
        "session_id": session_id,
        "answers": [
            {
                "question_code": "Q001",
                "selected_choices": ["web_app"]
            },
            {
                "question_code": "Q002", 
                "selected_choices": ["small"]
            },
            {
                "question_code": "Q003",
                "selected_choices": ["react", "python"]
            }
        ],
        "request_next_batch": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/questions/respond",
            headers=HEADERS,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API 2 Success!")
            print(f"   Response type: {data['response_type']}")
            print(f"   Completion: {data['completion_percentage']:.1f}%")
            print(f"   Message: {data['message']}")
            return data
        else:
            print(f"❌ API 2 Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ API 2 Error: {str(e)}")
        return None

def test_api_3_summary_generation(session_id: str):
    """Test API 3: Summary Generation"""
    print("\n🔄 Testing API 3: Summary Generation")
    
    payload = {
        "session_id": session_id,
        "include_assumptions": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/summary/generate",
            headers=HEADERS,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API 3 Success!")
            print(f"   Confidence score: {data['confidence_score']:.2f}")
            print(f"   Key points: {len(data['key_points'])}")
            print(f"   Assumptions: {len(data['assumptions'])}")
            
            # Confirm the summary
            confirm_payload = {
                "session_id": session_id,
                "confirmed": True,
                "additional_notes": "Summary looks good, ready to proceed."
            }
            
            confirm_response = requests.post(
                f"{API_BASE_URL}/v1/summary/confirm",
                headers=HEADERS,
                json=confirm_payload,
                timeout=10
            )
            
            if confirm_response.status_code == 200:
                print("✅ Summary confirmed successfully!")
                return data
            else:
                print(f"❌ Summary confirmation failed: {confirm_response.status_code}")
                return None
                
        else:
            print(f"❌ API 3 Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ API 3 Error: {str(e)}")
        return None

def test_api_4_document_generation(session_id: str):
    """Test API 4: Document Generation"""
    print("\n🔄 Testing API 4: Document Generation")
    
    payload = {
        "session_id": session_id,
        "format_type": "markdown",
        "include_implementation_details": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/documents/generate",
            headers=HEADERS,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API 4 Success!")
            print(f"   Stacks generated: {len(data['stacks'])}")
            print(f"   Total effort: {data['total_estimated_effort']}")
            print(f"   Timeline: {data['recommended_timeline']}")
            
            # Print stack information
            for stack in data['stacks']:
                print(f"   📋 {stack['title']}: {len(stack['technologies'])} technologies")
            
            return data
        else:
            print(f"❌ API 4 Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ API 4 Error: {str(e)}")
        return None

def test_health_endpoints():
    """Test health endpoints"""
    print("\n🔄 Testing Health Endpoints")
    
    endpoints = [
        "/health",
        "/v1/project/health", 
        "/v1/questions/health",
        "/v1/summary/health",
        "/v1/documents/health"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint}: OK")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: {str(e)}")

def main():
    """Run the complete API workflow test"""
    print("🚀 Starting IA Compose API Workflow Test")
    print("=" * 50)
    
    # Test health endpoints first (without auth)
    test_health_endpoints()
    
    # Test the complete 4-API workflow
    print("\n" + "=" * 50)
    print("🔗 Testing Complete 4-API Workflow")
    print("=" * 50)
    
    # API 1: Project Analysis
    project_data = test_api_1_project_analysis()
    if not project_data:
        print("❌ Workflow failed at API 1")
        return False
    
    session_id = project_data["session_id"]
    
    # API 2: Questions Response
    questions_data = test_api_2_questions_response(session_id)
    if not questions_data:
        print("❌ Workflow failed at API 2")
        return False
    
    # API 3: Summary Generation
    summary_data = test_api_3_summary_generation(session_id)
    if not summary_data:
        print("❌ Workflow failed at API 3")
        return False
    
    # API 4: Document Generation
    documents_data = test_api_4_document_generation(session_id)
    if not documents_data:
        print("❌ Workflow failed at API 4")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Complete Workflow Test PASSED!")
    print("=" * 50)
    print(f"Session ID: {session_id}")
    print("All 4 APIs working correctly in sequence!")
    
    return True

if __name__ == "__main__":
    print("IA Compose API Workflow Test")
    print("Make sure the API server is running on http://localhost:8001")
    print("Set DEMANDEI_API_KEY environment variable before starting the server")
    print()
    
    success = main()
    sys.exit(0 if success else 1)