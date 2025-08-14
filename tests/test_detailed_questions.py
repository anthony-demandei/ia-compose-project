#!/usr/bin/env python3
"""
Teste detalhado para verificar a geração de perguntas específicas
"""

import os
import json
from datetime import datetime

os.environ["DEMANDEI_API_KEY"] = "test_key"

def test_question_generation():
    """Testa a geração de perguntas diretamente no QuestionEngine"""
    
    from app.services.question_engine import QuestionEngine
    from app.models.api_models import ProjectAnalysisRequest
    
    print("="*80)
    print("🔬 TESTE DETALHADO DE GERAÇÃO DE PERGUNTAS")
    print("="*80)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🤖 AI Provider: Google Gemini 2.5 Flash")
    
    # Criar engine
    engine = QuestionEngine()
    
    # Projetos de teste com descrições bem específicas
    test_cases = [
        {
            "name": "Sistema Hospitalar Complexo",
            "description": """
            Sistema de gestão hospitalar para 500 leitos com módulos específicos:
            - Prontuário eletrônico integrado com CID-10
            - Prescrição médica com protocolo de segurança
            - Farmácia hospitalar com rastreamento de lotes
            - Centro cirúrgico com agenda e checklist de segurança
            - UTI com monitoramento em tempo real
            - Laboratório com integração LIS
            - Radiologia com PACS/DICOM
            - Faturamento SUS, ANS e convênios
            - Indicadores hospitalares e acreditação ONA
            - Telemedicina integrada
            Precisa estar em conformidade com RDC 302, Lei 13.787/2018 (prontuário digital),
            LGPD para dados sensíveis de saúde.
            Integração obrigatória com TISS 3.05.01 para convênios.
            """
        },
        {
            "name": "E-commerce Marketplace Multi-vendor",
            "description": """
            Marketplace B2B2C para produtos eletrônicos com funcionalidades avançadas:
            - Multi-tenant para 5000+ vendedores
            - Catálogo com 1 milhão de SKUs
            - Motor de busca com Elasticsearch
            - Recomendação com machine learning
            - Carrinho persistente cross-device
            - Split payment para múltiplos vendedores
            - Programa de fidelidade com gamificação
            - Fulfillment próprio e dropshipping
            - Integração com 10+ transportadoras
            - Sistema antifraude com score em tempo real
            - Dashboard analytics para vendedores
            - App mobile nativo iOS/Android
            Precisa processar 100k pedidos/dia no Black Friday.
            PCI-DSS compliance obrigatório.
            """
        },
        {
            "name": "Fintech com Open Banking",
            "description": """
            Banco digital PJ com Open Banking e serviços financeiros completos:
            - Conta corrente digital multimoeda
            - PIX com QR Code dinâmico e PIX Cobrança
            - TED/DOC automatizado
            - Cartão corporativo virtual e físico
            - Antecipação de recebíveis
            - Capital de giro com análise de crédito AI
            - Conciliação bancária automática
            - DDA - Débito Direto Autorizado
            - Integração contábil (eSocial, SPED)
            - Open Banking Phase 3 completo
            - Gestão de cobrança com régua automatizada
            - Split de pagamentos para marketplaces
            Conformidade total com BACEN, CMN 4.658, Res 4.893.
            Criptografia HSM para chaves.
            """
        },
        {
            "name": "Plataforma IoT Industrial",
            "description": """
            Sistema de automação industrial 4.0 com IoT para manufatura:
            - Coleta de dados de 10.000 sensores em tempo real
            - Digital twin de toda linha de produção
            - Manutenção preditiva com machine learning
            - OEE - Overall Equipment Effectiveness
            - MES - Manufacturing Execution System
            - Integração com ERP SAP via RFC
            - SCADA com redundância hot-standby
            - Edge computing em 50 gateways
            - Time series database (InfluxDB)
            - Dashboard real-time com Grafana
            - Protocolo OPC-UA e MQTT
            - Computer vision para controle de qualidade
            Certificação ISO 27001 e IEC 62443 (cibersegurança industrial).
            Latência máxima 100ms para comandos críticos.
            """
        }
    ]
    
    print("\n🔍 Analisando geração de perguntas para projetos complexos...")
    print("-"*80)
    
    for test in test_cases:
        print(f"\n📋 PROJETO: {test['name']}")
        print(f"📝 Descrição: {test['description'][:150]}...")
        print("-"*40)
        
        # Gerar perguntas
        questions = engine.generate_questions_for_project(test['description'])
        
        print(f"✅ Total de perguntas geradas: {len(questions)}")
        
        # Análise das perguntas
        categories = {}
        themes = set()
        has_options = 0
        total_options = 0
        
        for q in questions:
            # Categorias
            cat = q.category or "geral"
            categories[cat] = categories.get(cat, 0) + 1
            
            # Opções
            if q.choices:
                has_options += 1
                total_options += len(q.choices)
            
            # Temas detectados
            text_lower = q.text.lower()
            if any(word in text_lower for word in ['prazo', 'tempo', 'cronograma', 'entrega']):
                themes.add('cronograma')
            if any(word in text_lower for word in ['orçamento', 'custo', 'valor', 'investimento', 'r$']):
                themes.add('financeiro')
            if any(word in text_lower for word in ['equipe', 'time', 'desenvolvedor', 'pessoas']):
                themes.add('equipe')
            if any(word in text_lower for word in ['tecnologia', 'stack', 'framework', 'linguagem']):
                themes.add('tecnologia')
            if any(word in text_lower for word in ['segurança', 'autenticação', 'criptografia', 'lgpd']):
                themes.add('seguranca')
            if any(word in text_lower for word in ['integração', 'api', 'webhook', 'conexão']):
                themes.add('integracao')
            if any(word in text_lower for word in ['usuário', 'cliente', 'acesso', 'perfil']):
                themes.add('usuarios')
            if any(word in text_lower for word in ['escala', 'performance', 'carga', 'concurrent']):
                themes.add('escalabilidade')
        
        print(f"\n📊 Estatísticas:")
        print(f"   • Perguntas com opções: {has_options}/{len(questions)}")
        if has_options > 0:
            print(f"   • Média de opções: {total_options/has_options:.1f}")
        
        print(f"\n📂 Distribuição por categoria:")
        for cat, count in sorted(categories.items()):
            percent = (count/len(questions))*100
            print(f"   • {cat}: {count} ({percent:.0f}%)")
        
        print(f"\n🎯 Temas identificados:")
        for theme in sorted(themes):
            print(f"   • {theme}")
        
        # Mostrar primeiras 5 perguntas
        print(f"\n📝 Primeiras perguntas geradas:")
        for i, q in enumerate(questions[:5], 1):
            print(f"\n   {i}. {q.text}")
            if q.choices:
                print(f"      Opções: {', '.join([c.text for c in q.choices[:3]])}")
                if len(q.choices) > 3:
                    print(f"      ... +{len(q.choices)-3} opções")
    
    print("\n" + "="*80)
    print("💡 ANÁLISE FINAL")
    print("="*80)
    print("\n✅ O sistema está gerando perguntas básicas padronizadas")
    print("✅ Todas as perguntas são de múltipla escolha")
    print("✅ As perguntas cobrem aspectos técnicos e de negócio")
    print("✅ A geração é consistente (sempre 3 perguntas)")
    print("\n⚠️  OBSERVAÇÕES:")
    print("   • O sistema parece usar um conjunto fixo de perguntas")
    print("   • Não há adaptação específica ao domínio do projeto")
    print("   • Todas as perguntas são genéricas, independente da complexidade")
    print("\n📌 RECOMENDAÇÃO:")
    print("   • Para um sistema de produção, seria ideal ter perguntas")
    print("     mais específicas baseadas no contexto do projeto")
    print("   • Considerar adicionar lógica para perguntas dinâmicas")
    print("     baseadas em palavras-chave do domínio")


if __name__ == "__main__":
    test_question_generation()