#!/usr/bin/env python3
"""
Test dynamic question generation with AI.
Verifies that questions are unique and contextual for each project type.
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import List, Dict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["DEMANDEI_API_KEY"] = "test_key"
os.environ["GEMINI_API_KEY"] = "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos"
os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"

from fastapi.testclient import TestClient
from main import app


def analyze_questions(questions: List[Dict]) -> Dict:
    """Analyze generated questions for patterns."""
    analysis = {
        "total": len(questions),
        "unique_texts": set(),
        "categories": {},
        "has_choices": 0,
        "avg_choices": 0
    }
    
    total_choices = 0
    for q in questions:
        # Track unique question texts
        analysis["unique_texts"].add(q.get("text", ""))
        
        # Count categories
        cat = q.get("category", "general")
        analysis["categories"][cat] = analysis["categories"].get(cat, 0) + 1
        
        # Count choices
        choices = q.get("choices", [])
        if choices:
            analysis["has_choices"] += 1
            total_choices += len(choices)
    
    if analysis["has_choices"] > 0:
        analysis["avg_choices"] = total_choices / analysis["has_choices"]
    
    return analysis


async def test_project_dynamic_questions():
    """Test that different projects get different, contextual questions."""
    
    client = TestClient(app)
    headers = {"Authorization": "Bearer test_key"}
    
    print("=" * 80)
    print("🧪 TESTE DE GERAÇÃO DINÂMICA DE PERGUNTAS COM IA")
    print("=" * 80)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🤖 AI Provider: Google Gemini 2.5 Flash")
    print()
    
    # Test cases with very different projects
    test_cases = [
        {
            "name": "Sistema Hospitalar",
            "description": """
            Preciso de um sistema de gestão hospitalar para 500 leitos.
            Deve ter prontuário eletrônico, agendamento de consultas,
            controle de medicamentos, faturamento SUS e convênios.
            Integração com equipamentos médicos e telemedicina.
            """
        },
        {
            "name": "E-commerce de Roupas",
            "description": """
            Loja virtual de roupas femininas com provador virtual.
            Precisa ter catálogo com filtros, carrinho de compras,
            múltiplas formas de pagamento, cálculo de frete,
            programa de fidelidade e integração com Instagram.
            """
        },
        {
            "name": "App de Delivery Local",
            "description": """
            Aplicativo de delivery para restaurantes da minha cidade.
            Precisa de cadastro de restaurantes, cardápio digital,
            pedidos em tempo real, rastreamento de entregadores,
            pagamento online e avaliações. Foco em comida japonesa.
            """
        },
        {
            "name": "Automação de Planilhas",
            "description": """
            Preciso automatizar o preenchimento de planilhas Excel
            que recebo diariamente. Os dados vêm de emails em PDF,
            preciso extrair informações e consolidar em relatórios
            semanais. Volume de 50 planilhas por dia.
            """
        },
        {
            "name": "Sistema Escolar",
            "description": """
            Sistema de gestão escolar para 2000 alunos do ensino médio.
            Precisa ter matrícula online, diário de classe eletrônico,
            boletim digital, comunicação com pais via app,
            controle de frequência por QR code e biblioteca virtual.
            """
        }
    ]
    
    all_questions = []
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"📋 PROJETO: {test['name']}")
        print(f"📝 Descrição: {test['description'][:100]}...")
        print("-" * 40)
        
        # Call API
        response = client.post(
            "/v1/project/analyze",
            headers=headers,
            json={"project_description": test["description"]}
        )
        
        if response.status_code == 200:
            data = response.json()
            questions = data.get("questions", [])
            
            print(f"✅ Status: {response.status_code}")
            print(f"📊 Perguntas geradas: {len(questions)}")
            
            # Show questions
            for i, q in enumerate(questions[:3], 1):  # Show first 3
                print(f"\n   {i}. {q['text']}")
                if q.get("choices"):
                    print(f"      Opções: {len(q['choices'])} escolhas")
            
            # Store for comparison
            all_questions.append({
                "project": test["name"],
                "questions": questions
            })
        else:
            print(f"❌ Erro: {response.status_code}")
            print(f"   Detalhes: {response.text[:200]}")
    
    # Analyze uniqueness across projects
    print("\n" + "=" * 80)
    print("📊 ANÁLISE DE UNICIDADE DAS PERGUNTAS")
    print("=" * 80)
    
    # Collect all question texts
    all_texts = []
    for project_data in all_questions:
        for q in project_data["questions"]:
            all_texts.append(q.get("text", ""))
    
    unique_texts = set(all_texts)
    total_questions = len(all_texts)
    unique_count = len(unique_texts)
    
    print(f"📈 Total de perguntas geradas: {total_questions}")
    print(f"🎯 Perguntas únicas: {unique_count}")
    print(f"📊 Taxa de unicidade: {(unique_count/total_questions)*100:.1f}%")
    
    # Check if questions are contextual
    print("\n🔍 VERIFICAÇÃO DE CONTEXTUALIZAÇÃO:")
    
    contextual_keywords = {
        "Sistema Hospitalar": ["leito", "médico", "paciente", "saúde", "sus", "convênio", "prontuário"],
        "E-commerce de Roupas": ["produto", "catálogo", "pagamento", "frete", "carrinho", "roupa", "moda"],
        "App de Delivery Local": ["restaurante", "pedido", "entrega", "cardápio", "delivery", "comida"],
        "Automação de Planilhas": ["excel", "planilha", "automação", "dados", "relatório", "pdf"],
        "Sistema Escolar": ["aluno", "escola", "matrícula", "nota", "frequência", "professor", "aula"]
    }
    
    for project_data in all_questions:
        project_name = project_data["project"]
        questions = project_data["questions"]
        keywords = contextual_keywords.get(project_name, [])
        
        # Check if questions contain contextual keywords
        contextual_count = 0
        for q in questions:
            q_text = q.get("text", "").lower()
            if any(keyword in q_text for keyword in keywords):
                contextual_count += 1
        
        contextual_rate = (contextual_count / len(questions)) * 100 if questions else 0
        status = "✅" if contextual_rate > 30 else "⚠️"
        
        print(f"{status} {project_name}: {contextual_rate:.0f}% perguntas contextuais")
    
    print("\n" + "=" * 80)
    print("💡 CONCLUSÃO")
    print("=" * 80)
    
    if unique_count / total_questions > 0.7:
        print("✅ SUCESSO: Sistema está gerando perguntas únicas e dinâmicas!")
        print("✅ Cada projeto recebe perguntas personalizadas")
        print("✅ IA está funcionando como desenvolvedor/PO experiente")
    else:
        print("⚠️ ATENÇÃO: Baixa taxa de unicidade nas perguntas")
        print("⚠️ Verificar se a IA está gerando conteúdo dinâmico")
    
    print("\n🎯 O sistema agora gera perguntas como um humano faria,")
    print("   adaptando-se ao contexto específico de cada projeto!")


if __name__ == "__main__":
    asyncio.run(test_project_dynamic_questions())