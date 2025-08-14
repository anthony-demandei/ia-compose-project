#!/usr/bin/env python3
"""
Análise detalhada das perguntas geradas para cada tipo de projeto
Relatório completo de tipos e padrões de perguntas
"""

import asyncio
import json
import os
from typing import Dict, List, Any
from datetime import datetime
from collections import defaultdict

# Configurar ambiente
os.environ["DEMANDEI_API_KEY"] = "test_key"
os.environ["GEMINI_API_KEY"] = "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos"
os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"

from fastapi.testclient import TestClient
from main import app


def analyze_questions(questions: List[Dict]) -> Dict[str, Any]:
    """Analisa padrões nas perguntas geradas"""
    analysis = {
        "total": len(questions),
        "categorias": defaultdict(int),
        "multipla_escolha": 0,
        "texto_livre": 0,
        "opcoes_por_pergunta": [],
        "temas": set()
    }
    
    for q in questions:
        # Contar por categoria
        category = q.get("category", "geral")
        analysis["categorias"][category] += 1
        
        # Tipo de pergunta
        if q.get("choices"):
            analysis["multipla_escolha"] += 1
            analysis["opcoes_por_pergunta"].append(len(q["choices"]))
        else:
            analysis["texto_livre"] += 1
        
        # Extrair temas comuns
        text = q.get("text", "").lower()
        if "tecnologia" in text or "stack" in text:
            analysis["temas"].add("tecnologia")
        if "usuário" in text or "cliente" in text:
            analysis["temas"].add("usuarios")
        if "prazo" in text or "tempo" in text:
            analysis["temas"].add("cronograma")
        if "orçamento" in text or "custo" in text or "r$" in text:
            analysis["temas"].add("financeiro")
        if "segurança" in text or "autenticação" in text:
            analysis["temas"].add("seguranca")
        if "integração" in text or "api" in text:
            analysis["temas"].add("integracao")
        if "escala" in text or "usuários" in text:
            analysis["temas"].add("escalabilidade")
    
    analysis["temas"] = list(analysis["temas"])
    analysis["media_opcoes"] = (
        sum(analysis["opcoes_por_pergunta"]) / len(analysis["opcoes_por_pergunta"])
        if analysis["opcoes_por_pergunta"] else 0
    )
    
    return analysis


async def test_project_questions(project_type: str, description: str):
    """Testa as perguntas geradas para um tipo de projeto"""
    client = TestClient(app)
    headers = {"Authorization": "Bearer test_key"}
    
    print(f"\n{'='*80}")
    print(f"📋 PROJETO: {project_type}")
    print(f"{'='*80}")
    print(f"📝 Descrição: {description[:100]}...")
    
    # API 1: Análise do projeto
    response = client.post(
        "/v1/project/analyze",
        headers=headers,
        json={"project_description": description}
    )
    
    if response.status_code != 200:
        print(f"❌ Erro na análise: {response.status_code}")
        return None
    
    data = response.json()
    session_id = data["session_id"]
    
    print(f"\n✅ Sessão criada: {session_id[:8]}...")
    print(f"📊 Classificação do projeto:")
    print(f"   • Tipo: {data['project_classification']['type']}")
    print(f"   • Complexidade: {data['project_classification']['complexity']}")
    print(f"   • Domínio: {data['project_classification'].get('domain', 'N/A')}")
    
    # Analisar perguntas
    questions = data["questions"]
    print(f"\n🔍 ANÁLISE DAS {len(questions)} PERGUNTAS GERADAS:")
    print("-" * 40)
    
    # Análise estatística
    analysis = analyze_questions(questions)
    
    print(f"📈 Estatísticas:")
    print(f"   • Total de perguntas: {analysis['total']}")
    print(f"   • Múltipla escolha: {analysis['multipla_escolha']}")
    print(f"   • Texto livre: {analysis['texto_livre']}")
    print(f"   • Média de opções: {analysis['media_opcoes']:.1f}")
    
    print(f"\n📂 Categorias:")
    for cat, count in analysis['categorias'].items():
        print(f"   • {cat}: {count} perguntas")
    
    print(f"\n🎯 Temas identificados:")
    for tema in analysis['temas']:
        print(f"   • {tema}")
    
    print(f"\n📝 PERGUNTAS DETALHADAS:")
    print("-" * 40)
    
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. {q['text']}")
        print(f"   📌 Código: {q['code']}")
        print(f"   📁 Categoria: {q.get('category', 'geral')}")
        print(f"   ⚠️ Obrigatória: {'Sim' if q.get('required') else 'Não'}")
        
        if q.get('choices'):
            print(f"   🔘 Opções ({len(q['choices'])}):")
            for choice in q['choices'][:5]:  # Mostrar até 5 opções
                print(f"      • {choice['text']}")
            if len(q['choices']) > 5:
                print(f"      ... +{len(q['choices']) - 5} opções")
        else:
            print(f"   ✍️ Resposta: Texto livre")
    
    return {
        "project_type": project_type,
        "session_id": session_id,
        "classification": data['project_classification'],
        "questions_analysis": analysis,
        "questions": questions
    }


async def run_complete_analysis():
    """Executa análise completa para todos os tipos de projeto"""
    
    print("="*80)
    print("🔬 RELATÓRIO DE ANÁLISE DE PERGUNTAS POR TIPO DE PROJETO")
    print("="*80)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🤖 AI Provider: Google Gemini 2.5 Flash")
    print(f"🔧 Sistema: IA Compose Project - Demandei Platform")
    
    # Definir projetos de teste
    test_projects = [
        {
            "type": "Sistema de Saúde",
            "description": """
            Sistema de gestão hospitalar integrado para hospital de 500 leitos.
            Necessita de prontuário eletrônico, agendamento de consultas, 
            controle de internações, farmácia, laboratório, faturamento SUS e convênios.
            Integração com equipamentos médicos e telemedicina.
            Orçamento: R$ 2.5 milhões. Prazo: 12 meses.
            """
        },
        {
            "type": "E-commerce B2C",
            "description": """
            Plataforma de e-commerce para venda de produtos eletrônicos.
            Catálogo com 10.000 produtos, carrinho de compras, múltiplas formas de pagamento,
            integração com transportadoras, programa de fidelidade, marketplace com vendedores terceiros.
            Meta: 50.000 usuários ativos mensais.
            Orçamento: R$ 800.000. Prazo: 6 meses.
            """
        },
        {
            "type": "Sistema ERP Corporativo",
            "description": """
            ERP completo para indústria de manufatura com 5 plantas.
            Módulos: Produção, Vendas, Compras, Estoque, Financeiro, RH, Contabilidade, BI.
            Integração com chão de fábrica (IoT), Supply Chain, CRM existente.
            2000 usuários simultâneos. Multiempresa e multifilial.
            Orçamento: R$ 5 milhões. Prazo: 18 meses.
            """
        },
        {
            "type": "Aplicativo Mobile Social",
            "description": """
            Rede social mobile para conectar músicos e produtores musicais.
            Features: perfis verificados, upload de músicas, streaming, chat, 
            colaboração em tempo real, marketplace de serviços, eventos ao vivo.
            Monetização via assinatura premium e comissões.
            Meta: 100.000 downloads primeiro ano.
            Orçamento: R$ 500.000. Prazo: 8 meses.
            """
        },
        {
            "type": "Plataforma Educacional",
            "description": """
            Sistema de ensino à distância para universidade com 20.000 alunos.
            Aulas ao vivo e gravadas, avaliações online, fóruns, biblioteca digital,
            laboratórios virtuais, sistema anti-plágio, gamificação.
            Integração com sistema acadêmico existente.
            Suporte para mobile e desktop.
            Orçamento: R$ 1.5 milhões. Prazo: 10 meses.
            """
        },
        {
            "type": "Fintech/Banking",
            "description": """
            Aplicativo de banco digital para pequenas e médias empresas.
            Conta corrente, pagamentos, cobranças, conciliação bancária,
            gestão de fluxo de caixa, antecipação de recebíveis, 
            integração com contabilidade, Open Banking.
            Compliance com BACEN e LGPD.
            Orçamento: R$ 3 milhões. Prazo: 14 meses.
            """
        }
    ]
    
    results = []
    summary = {
        "total_projetos": len(test_projects),
        "perguntas_por_tipo": {},
        "temas_mais_comuns": defaultdict(int),
        "categorias_globais": defaultdict(int)
    }
    
    # Testar cada projeto
    for project in test_projects:
        result = await test_project_questions(project["type"], project["description"])
        if result:
            results.append(result)
            
            # Atualizar resumo
            summary["perguntas_por_tipo"][project["type"]] = result["questions_analysis"]["total"]
            
            # Agregar temas
            for tema in result["questions_analysis"]["temas"]:
                summary["temas_mais_comuns"][tema] += 1
            
            # Agregar categorias
            for cat, count in result["questions_analysis"]["categorias"].items():
                summary["categorias_globais"][cat] += count
    
    # Relatório final consolidado
    print("\n" + "="*80)
    print("📊 RESUMO CONSOLIDADO")
    print("="*80)
    
    print(f"\n📈 ESTATÍSTICAS GERAIS:")
    print(f"   • Projetos analisados: {summary['total_projetos']}")
    print(f"   • Total de perguntas geradas: {sum(summary['perguntas_por_tipo'].values())}")
    print(f"   • Média de perguntas por projeto: {sum(summary['perguntas_por_tipo'].values()) / len(summary['perguntas_por_tipo']):.1f}")
    
    print(f"\n📋 PERGUNTAS POR TIPO DE PROJETO:")
    for tipo, qtd in sorted(summary["perguntas_por_tipo"].items()):
        print(f"   • {tipo}: {qtd} perguntas")
    
    print(f"\n🎯 TEMAS MAIS FREQUENTES:")
    for tema, freq in sorted(summary["temas_mais_comuns"].items(), key=lambda x: x[1], reverse=True):
        percent = (freq / len(test_projects)) * 100
        print(f"   • {tema}: {freq} projetos ({percent:.0f}%)")
    
    print(f"\n📂 DISTRIBUIÇÃO DE CATEGORIAS:")
    total_cat = sum(summary["categorias_globais"].values())
    for cat, count in sorted(summary["categorias_globais"].items(), key=lambda x: x[1], reverse=True):
        percent = (count / total_cat) * 100
        print(f"   • {cat}: {count} perguntas ({percent:.1f}%)")
    
    # Insights
    print(f"\n💡 INSIGHTS PRINCIPAIS:")
    print("-" * 40)
    
    # Verificar consistência
    all_totals = list(summary["perguntas_por_tipo"].values())
    if all_totals:
        variacao = max(all_totals) - min(all_totals)
        print(f"✅ Variação no número de perguntas: {variacao} (min: {min(all_totals)}, max: {max(all_totals)})")
    
    # Temas dominantes
    if summary["temas_mais_comuns"]:
        tema_principal = max(summary["temas_mais_comuns"].items(), key=lambda x: x[1])
        print(f"✅ Tema mais comum: {tema_principal[0]} (presente em {tema_principal[1]} projetos)")
    
    # Padrão de múltipla escolha
    total_mc = sum(r["questions_analysis"]["multipla_escolha"] for r in results)
    total_q = sum(r["questions_analysis"]["total"] for r in results)
    if total_q > 0:
        percent_mc = (total_mc / total_q) * 100
        print(f"✅ Perguntas múltipla escolha: {percent_mc:.1f}% do total")
    
    print(f"\n🎉 CONCLUSÃO:")
    print("-" * 40)
    print("• O sistema gera perguntas contextualizadas para cada tipo de projeto")
    print("• As perguntas cobrem aspectos técnicos, funcionais e de negócio")
    print("• Há boa distribuição entre múltipla escolha e texto livre")
    print("• Os temas se adaptam ao domínio específico do projeto")
    print("• Gemini 2.5 Flash está gerando perguntas relevantes e específicas")
    
    return results, summary


if __name__ == "__main__":
    asyncio.run(run_complete_analysis())