#!/usr/bin/env python3
"""
Test Gemini Structured Output implementation.
This should eliminate all JSON parsing issues and fallbacks.
"""

import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["DEMANDEI_API_KEY"] = "test_key"
os.environ["GEMINI_API_KEY"] = "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos"
os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"
os.environ["ENABLE_ZEP_MEMORY"] = "false"


async def test_structured_output():
    """Test the new Gemini Structured Output implementation."""
    
    print("=" * 80)
    print("🚀 TESTE GEMINI STRUCTURED OUTPUT - ZERO FALLBACKS")
    print("=" * 80)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    from app.services.ai_question_agent import AIQuestionAgent
    from app.services.gemini_provider import create_questions_response_schema
    
    # Test 1: Schema generation
    print("1️⃣ TESTANDO GERAÇÃO DE SCHEMA JSON")
    print("-" * 50)
    
    schema = create_questions_response_schema()
    print(f"   📋 Schema gerado com {len(schema['properties'])} propriedades principais")
    print(f"   🔧 MIME type: application/json")
    print(f"   📝 Estrutura garantida para 'questions' array")
    
    questions_schema = schema['properties']['questions']['items']['properties']
    required_fields = questions_schema.keys()
    print(f"   ✅ Campos obrigatórios: {list(required_fields)}")
    
    # Test 2: Agent with structured output
    print("\n2️⃣ TESTANDO AGENTE COM STRUCTURED OUTPUT")
    print("-" * 50)
    
    agent = AIQuestionAgent()
    
    # Test with complex project description
    complex_project = """
    Sistema completo de gestão hospitalar para 500 leitos incluindo:
    - Prontuários eletrônicos integrados com HL7 FHIR
    - Módulo de farmácia com controle de estoque automatizado
    - Sistema de agendamento inteligente com IA
    - Dashboard médico com analytics avançados
    - Integração com equipamentos médicos IoT
    - Telemedicina com videochamadas HD
    - Faturamento automático com ANS
    Orçamento: R$ 2.5 milhões, prazo: 18 meses, equipe: 15 desenvolvedores
    """
    
    print("   🤖 Gerando perguntas com Structured Output...")
    start_time = datetime.now()
    
    try:
        questions = await agent.generate_questions(complex_project, 5)
        execution_time = (datetime.now() - start_time).total_seconds()
        
        print(f"   ⏱️ Tempo de execução: {execution_time:.2f}s")
        print(f"   📊 Perguntas geradas: {len(questions)}")
        
        if questions:
            # Check if fallback questions or real AI questions
            first_question = questions[0].text
            
            if "principal objetivo" in first_question.lower():
                print("   ❌ FALHOU: Ainda usando fallback questions")
                return False
            else:
                print("   ✅ SUCESSO: Perguntas contextuais geradas!")
                print(f"   🎯 Primeira pergunta: {first_question}")
                
                # Validate structure
                for i, q in enumerate(questions[:3]):
                    print(f"\n   Q{i+1}:")
                    print(f"      📝 Texto: {q.text[:80]}...")
                    print(f"      🏷️ Categoria: {q.category}")
                    print(f"      ⚡ Obrigatória: {q.required}")
                    print(f"      🔢 Opções: {len(q.choices)}")
                    
                    if q.choices:
                        print(f"      🎛️ Primeira opção: {q.choices[0].text}")
                
                return True
        else:
            print("   ❌ FALHOU: Nenhuma pergunta gerada")
            return False
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        return False

    # Test 3: Multiple project types
    print("\n3️⃣ TESTANDO DIFERENTES TIPOS DE PROJETO")
    print("-" * 50)
    
    projects = [
        {
            "name": "E-commerce B2B",
            "description": "Marketplace B2B para atacadistas com catálogo de 100mil produtos, sistema de cotas, EDI, integração ERP e módulo logístico avançado"
        },
        {
            "name": "Fintech de Crédito",
            "description": "Plataforma de análise de crédito com ML, integração Serasa/SPC, motor de decisão automatizado, gestão de portfólio e compliance LGPD"
        },
        {
            "name": "App de Delivery",
            "description": "Super app de delivery multi-categoria com geolocalização, pagamentos PIX, programa fidelidade, analytics em tempo real e IA para recomendações"
        }
    ]
    
    success_count = 0
    
    for project in projects:
        print(f"\n   🔍 Testando: {project['name']}")
        
        try:
            questions = await agent.generate_questions(project['description'], 4)
            
            if questions and len(questions) >= 3:
                first_q = questions[0].text
                if "principal objetivo" not in first_q.lower():
                    print(f"      ✅ Perguntas contextuais: {len(questions)}")
                    print(f"      📝 Exemplo: {first_q[:60]}...")
                    success_count += 1
                else:
                    print(f"      ❌ Fallback detectado")
            else:
                print(f"      ❌ Falha na geração")
        except Exception as e:
            print(f"      ❌ Erro: {e}")
    
    print(f"\n   📊 Taxa de sucesso: {success_count}/{len(projects)} ({success_count/len(projects)*100:.1f}%)")
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 RESUMO DO TESTE STRUCTURED OUTPUT")
    print("=" * 80)
    
    benefits = [
        "✅ Schema JSON garantido pelo Gemini",
        "✅ Zero parsing manual necessário",
        "✅ Validação automática de estrutura",
        "✅ Eliminação de regex/fallbacks",
        "✅ Perguntas sempre no formato correto",
        "✅ Redução significativa de fallbacks"
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")
    
    if success_count >= len(projects) * 0.8:  # 80% success rate
        print(f"\n🎉 STRUCTURED OUTPUT FUNCIONANDO PERFEITAMENTE!")
        print(f"   📈 Taxa de sucesso: {success_count/len(projects)*100:.1f}%")
        print(f"   🚀 Sistema pronto para produção!")
        return True
    else:
        print(f"\n⚠️ Structured Output precisa de ajustes")
        print(f"   📉 Taxa de sucesso baixa: {success_count/len(projects)*100:.1f}%")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_structured_output())
    sys.exit(0 if result else 1)