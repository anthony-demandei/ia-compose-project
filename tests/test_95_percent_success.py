#!/usr/bin/env python3
"""
Teste específico para validar taxa de sucesso de 95%+ após otimizações de safety settings.
Baseado nas melhorias implementadas para reduzir safety blocks do Gemini.
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
os.environ["ENABLE_ZEP_MEMORY"] = "false"


async def test_95_percent_success_rate():
    """Teste rigoroso para validar taxa de sucesso de 95%+ conforme exigido."""
    
    print("=" * 80)
    print("🎯 TESTE RIGOROSO: VALIDAÇÃO 95%+ TAXA DE SUCESSO")
    print("=" * 80)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Meta: 95% mínimo conforme especificado")
    print()
    
    from app.services.ai_question_agent import AIQuestionAgent
    
    # Projetos diversos para teste abrangente
    test_projects = [
        {
            "name": "Sistema Hospitalar",
            "description": "Sistema completo de gestão hospitalar para 500 leitos incluindo prontuários eletrônicos integrados com HL7 FHIR, módulo de farmácia com controle de estoque automatizado, sistema de agendamento inteligente com IA, dashboard médico com analytics avançados, integração com equipamentos médicos IoT, telemedicina com videochamadas HD e faturamento automático com ANS. Orçamento: R$ 2.5 milhões, prazo: 18 meses, equipe: 15 desenvolvedores."
        },
        {
            "name": "E-commerce B2B",
            "description": "Marketplace B2B para atacadistas com catálogo de 100mil produtos, sistema de cotas personalizadas, integração EDI com fornecedores, módulo logístico avançado com tracking em tempo real, sistema de crédito automático, dashboard analytics, módulo fiscal completo e integração com ERPs diversos. Orçamento: R$ 800 mil, prazo: 12 meses."
        },
        {
            "name": "Fintech de Crédito",
            "description": "Plataforma de análise de crédito com machine learning, integração completa Serasa/SPC/Bacen, motor de decisão automatizado, gestão de portfólio de investidores, compliance LGPD, Open Banking, scoring proprietário, API para parceiros e dashboard regulatório. Capital inicial: R$ 5 milhões, equipe: 25 pessoas."
        },
        {
            "name": "App de Delivery",
            "description": "Super app de delivery multi-categoria com geolocalização avançada, pagamentos PIX/cartão, programa de fidelidade gamificado, analytics em tempo real, IA para recomendações, sistema de chat, avaliações, multiple vendors, tracking GPS e módulo de entregadores. Investimento: R$ 2 milhões, MVP em 6 meses."
        },
        {
            "name": "Sistema ERP Industrial",
            "description": "ERP completo para indústria metalúrgica com módulos de produção, qualidade, manutenção preventiva, gestão de frotas, integração com máquinas CNC, controle de estoque FIFO, custos por centro, BI avançado, móbile para chão de fábrica e compliance fiscal/trabalhista. R$ 1.2 milhão, 14 meses."
        },
        {
            "name": "Plataforma Educacional",
            "description": "LMS corporativo para empresas com trilhas de aprendizagem personalizadas, gamificação, videoconferência integrada, avaliações adaptatvas com IA, certificações digitais, analytics de performance, integração RH/folha, mobile learning e módulo social. 50mil usuários esperados, R$ 600 mil."
        },
        {
            "name": "Sistema de Telecomunicações",
            "description": "Plataforma OSS/BSS para operadoras de telecom com provisionamento automático, billing em tempo real, gestão de SLA, monitoramento de rede, trouble ticketing, CRM integrado, portal do cliente, APIs para parceiros e compliance Anatel. Projeto crítico: R$ 3 milhões, 20 meses."
        },
        {
            "name": "Banking Digital",
            "description": "Core bancário digital completo com conta corrente, poupança, investimentos, cartões, empréstimos, seguros, Open Banking, PIX, TED/DOC, analytics antifraude com IA, compliance Bacen, KYC automatizado e onboarding digital. Regulamentação crítica, R$ 10 milhões."
        },
        {
            "name": "Sistema de Logística",
            "description": "WMS/TMS integrado para operadores logísticos com otimização de rotas por IA, controle de frota em tempo real, integração EDI, track and trace para clientes, gestão de armazéns automatizados, billing automático, dashboard executivo e APIs para e-commerces. R$ 900 mil, 10 meses."
        },
        {
            "name": "Plataforma IoT Industrial",
            "description": "Sistema de monitoramento industrial IoT com sensores diversos, edge computing, análise preditiva de falhas, dashboards em tempo real, alertas inteligentes, integração com sistemas legados, APIs RESTful, machine learning para otimização e compliance Industry 4.0. R$ 1.5 milhão, 16 meses."
        }
    ]
    
    agent = AIQuestionAgent()
    results = []
    total_tests = len(test_projects)
    
    print(f"🧪 EXECUTANDO {total_tests} TESTES RIGOROSOS")
    print("-" * 50)
    
    for i, project in enumerate(test_projects):
        print(f"\n🔍 Teste {i+1}/{total_tests}: {project['name']}")
        
        start_time = datetime.now()
        success = False
        questions_count = 0
        error_type = "unknown"
        
        try:
            questions = await agent.generate_questions(project['description'], 5)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if questions and len(questions) >= 3:
                # Verificar se são perguntas contextuais (não fallback)
                first_question = questions[0].text.lower()
                is_fallback = "principal objetivo" in first_question
                
                if not is_fallback:
                    success = True
                    questions_count = len(questions)
                    print(f"   ✅ SUCESSO: {questions_count} perguntas em {execution_time:.2f}s")
                    print(f"   📝 Exemplo: {questions[0].text[:70]}...")
                else:
                    error_type = "fallback_questions"
                    print(f"   ❌ FALLBACK: Perguntas genéricas detectadas")
            else:
                error_type = "insufficient_questions"
                print(f"   ❌ FALHA: Apenas {len(questions) if questions else 0} perguntas geradas")
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_type = type(e).__name__
            print(f"   ❌ ERRO: {e}")
        
        results.append({
            "project": project['name'],
            "success": success,
            "questions_count": questions_count,
            "execution_time": execution_time,
            "error_type": error_type if not success else None
        })
    
    # Análise dos resultados
    print("\n" + "=" * 80)
    print("📊 ANÁLISE DETALHADA DOS RESULTADOS")
    print("=" * 80)
    
    successful_tests = sum(1 for r in results if r['success'])
    success_rate = (successful_tests / total_tests) * 100
    
    print(f"📈 Taxa de Sucesso: {successful_tests}/{total_tests} ({success_rate:.1f}%)")
    print(f"🎯 Meta Exigida: 95.0%")
    print(f"📊 Status: {'✅ APROVADO' if success_rate >= 95.0 else '❌ REPROVADO'}")
    
    if success_rate >= 95.0:
        print(f"\n🎉 PARABÉNS! Meta de 95%+ atingida com {success_rate:.1f}%")
        print("✅ Sistema pronto para produção!")
        
        # Estatísticas de performance
        avg_time = sum(r['execution_time'] for r in results if r['success']) / successful_tests
        avg_questions = sum(r['questions_count'] for r in results if r['success']) / successful_tests
        
        print(f"\n📊 ESTATÍSTICAS DE PERFORMANCE:")
        print(f"   ⏱️ Tempo médio: {avg_time:.2f}s")
        print(f"   📝 Perguntas médias: {avg_questions:.1f}")
        
    else:
        print(f"\n⚠️ Meta não atingida: {success_rate:.1f}% < 95%")
        print("🔧 Análise de falhas:")
        
        # Contar tipos de erro
        error_counts = {}
        for r in results:
            if not r['success'] and r['error_type']:
                error_counts[r['error_type']] = error_counts.get(r['error_type'], 0) + 1
        
        for error_type, count in error_counts.items():
            print(f"   • {error_type}: {count} ocorrências")
        
        print("\n🔧 PRÓXIMAS AÇÕES RECOMENDADAS:")
        if 'safety_block' in str(error_counts):
            print("   1. Ajustar ainda mais os safety settings")
            print("   2. Simplificar prompts adicionalmente")
        if 'fallback_questions' in str(error_counts):
            print("   3. Melhorar detection de fallback")
            print("   4. Revisar system instructions")
        print("   5. Analisar logs detalhados dos failures")
    
    # Resumo por categoria de projeto
    print(f"\n📋 DETALHAMENTO POR PROJETO:")
    for result in results:
        status_icon = "✅" if result['success'] else "❌"
        print(f"   {status_icon} {result['project']}: {result['questions_count']} perguntas em {result['execution_time']:.2f}s")
    
    print("\n" + "=" * 80)
    print("🏁 TESTE CONCLUÍDO")
    print("=" * 80)
    
    return success_rate >= 95.0


if __name__ == "__main__":
    result = asyncio.run(test_95_percent_success_rate())
    print(f"\n{'✅ SUCESSO' if result else '❌ FALHA'}: Teste de 95% taxa de sucesso")
    sys.exit(0 if result else 1)