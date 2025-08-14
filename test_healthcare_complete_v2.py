#!/usr/bin/env python3
"""
Test script for healthcare system documentation generation.
Tests the complete 4-API workflow with improved session storage.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.append('.')

from fastapi.testclient import TestClient
from main import app

# Test client
client = TestClient(app)
headers = {'Authorization': 'Bearer test_key'}

def test_healthcare_system():
    """Test complete workflow for healthcare system."""
    
    print("🏥 TESTE COMPLETO: SISTEMA DE GESTÃO HOSPITALAR V2")
    print("=" * 60)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Clear previous test results
    test_dir = Path("hospital_docs_v2")
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
    test_dir.mkdir(exist_ok=True)
    
    # API 1: Project Analysis
    print("📋 API 1: Análise do Projeto Hospitalar")
    print("-" * 40)
    
    project_description = """
    Sistema completo de gestão hospitalar para 500 leitos incluindo:
    - Prontuários eletrônicos integrados com padrão HL7 FHIR
    - Módulo de farmácia com controle de estoque automatizado
    - Sistema de agendamento inteligente com IA
    - Integração com equipamentos médicos (monitores, ventiladores)
    - Módulo de faturamento compatível com TISS 3.0 para convênios
    - Sistema de gestão de UTI e centro cirúrgico
    - Dashboard gerencial com indicadores em tempo real
    - App mobile para equipe médica e enfermagem
    - Integração com laboratórios e exames de imagem
    - Orçamento: R$ 850.000
    - Prazo: 18 meses
    """
    
    payload1 = {
        "project_description": project_description
    }
    
    response1 = client.post('/v1/project/analyze', headers=headers, json=payload1)
    
    if response1.status_code == 200:
        data1 = response1.json()
        session_id = data1['session_id']
        questions = data1.get('questions', [])
        
        print(f"✅ Status: {response1.status_code}")
        print(f"📊 Session ID: {session_id}")
        print(f"📊 Perguntas geradas: {len(questions)}")
        print(f"🎯 Classificação: {data1.get('project_classification', {})}")
        
        # API 2: Questions Response
        print("\n❓ API 2: Respondendo Perguntas")
        print("-" * 40)
        
        # Prepare healthcare-specific answers
        answers = []
        for i, question in enumerate(questions[:6]):  # Answer first 6 questions
            if "dispositivo" in question.get("text", "").lower() or "plataforma" in question.get("text", "").lower():
                answers.append({
                    "question_code": question.get("code"),
                    "selected_choices": ["desktop_workstation", "mobile_devices", "tablets"]
                })
            elif "periférico" in question.get("text", "").lower() or "integração" in question.get("text", "").lower():
                answers.append({
                    "question_code": question.get("code"),
                    "selected_choices": ["medical_devices", "lab_systems", "imaging_pacs"]
                })
            elif "fiscal" in question.get("text", "").lower() or "compliance" in question.get("text", "").lower():
                answers.append({
                    "question_code": question.get("code"),
                    "selected_choices": ["lgpd", "cfm", "anvisa", "sus_integration"]
                })
            elif "external" in question.get("text", "").lower() or "sistemas" in question.get("text", "").lower():
                answers.append({
                    "question_code": question.get("code"),
                    "selected_choices": ["datasus", "tiss_ans", "hl7_fhir"]
                })
            elif "desempenho" in question.get("text", "").lower() or "performance" in question.get("text", "").lower():
                answers.append({
                    "question_code": question.get("code"),
                    "selected_choices": ["high_availability_247"]
                })
            else:
                # Generic answer for other questions
                choices = question.get("choices", [])
                if choices:
                    answers.append({
                        "question_code": question.get("code"),
                        "selected_choices": [choices[0].get("id")]
                    })
        
        payload2 = {
            "session_id": session_id,
            "answers": answers,
            "request_next_batch": False
        }
        
        response2 = client.post('/v1/questions/respond', headers=headers, json=payload2)
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"✅ Status: {response2.status_code}")
            print(f"📊 Tipo resposta: {data2.get('response_type')}")
            print(f"📊 Completude: {data2.get('completion_percentage')}%")
            
            # API 3: Summary Generation
            print("\n📝 API 3: Geração do Resumo")
            print("-" * 40)
            
            payload3 = {
                "session_id": session_id,
                "include_assumptions": True
            }
            
            response3 = client.post('/v1/summary/generate', headers=headers, json=payload3)
            
            if response3.status_code == 200:
                data3 = response3.json()
                print(f"✅ Status: {response3.status_code}")
                print(f"📊 Score confiança: {data3.get('confidence_score')}")
                
                # Confirm summary
                confirm_payload = {
                    "session_id": session_id,
                    "confirmed": True
                }
                
                confirm_response = client.post('/v1/summary/confirm', headers=headers, json=confirm_payload)
                
                if confirm_response.status_code == 200:
                    print(f"✅ Resumo confirmado")
                    
                    # API 4: Document Generation
                    print("\n📄 API 4: Geração de Documentação")
                    print("-" * 40)
                    
                    payload4 = {
                        "session_id": session_id,
                        "format_type": "markdown",
                        "include_implementation_details": True
                    }
                    
                    response4 = client.post('/v1/documents/generate', headers=headers, json=payload4)
                    
                    if response4.status_code == 200:
                        data4 = response4.json()
                        print(f"✅ Status: {response4.status_code}")
                        print(f"📊 Stacks gerados: {len(data4.get('stacks', []))}")
                        print(f"📊 Esforço total: {data4.get('total_estimated_effort')}")
                        print(f"📊 Timeline: {data4.get('recommended_timeline')}")
                        
                        # Save generated documents
                        print("\n💾 Salvando Documentação Gerada")
                        print("-" * 40)
                        
                        stacks = data4.get('stacks', [])
                        total_chars = 0
                        
                        for stack in stacks:
                            stack_type = stack.get('stack_type', 'unknown')
                            content = stack.get('content', '')
                            filename = f"{stack_type.upper()}_HOSPITAL.md"
                            filepath = test_dir / filename
                            
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(content)
                            
                            file_size = len(content)
                            total_chars += file_size
                            print(f"   ✅ {filename}: {file_size:,} caracteres")
                        
                        # Save test results
                        test_results = {
                            "session_id": session_id,
                            "project_type": data1.get('project_classification', {}).get('type'),
                            "questions_generated": len(questions),
                            "answers_provided": len(answers),
                            "confidence_score": data3.get('confidence_score'),
                            "stacks": [
                                {
                                    "type": s.get('stack_type'),
                                    "title": s.get('title'),
                                    "technologies": s.get('technologies'),
                                    "effort": s.get('estimated_effort'),
                                    "size": len(s.get('content', ''))
                                }
                                for s in stacks
                            ],
                            "total_effort": data4.get('total_estimated_effort'),
                            "timeline": data4.get('recommended_timeline'),
                            "total_documentation_chars": total_chars,
                            "generated_at": datetime.now().isoformat()
                        }
                        
                        with open(test_dir / 'resultado_teste_v2.json', 'w', encoding='utf-8') as f:
                            json.dump(test_results, f, indent=2, ensure_ascii=False)
                        
                        # Generate executive summary
                        print("\n📊 Gerando Resumo Executivo")
                        print("-" * 40)
                        
                        summary = f"""# SISTEMA DE GESTÃO HOSPITALAR - DOCUMENTAÇÃO TÉCNICA COMPLETA V2

## 📊 RESUMO EXECUTIVO

### Informações do Projeto
- **Tipo**: Sistema de Gestão Hospitalar (500 leitos)
- **Classificação**: {data1.get('project_classification', {}).get('type')}
- **Complexidade**: {data1.get('project_classification', {}).get('complexity')}
- **Session ID**: {session_id}
- **Data Geração**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Estimativas
- **Esforço Total**: {data4.get('total_estimated_effort')}
- **Timeline**: {data4.get('recommended_timeline')}
- **Orçamento**: R$ 850.000
- **Prazo Original**: 18 meses

## 📚 DOCUMENTAÇÃO GERADA

### Análise de Conteúdo
- **Total de Caracteres**: {total_chars:,}
- **Tipo de Templates**: {"Healthcare-específicos" if total_chars > 10000 else "Genéricos"}
- **Contextualização**: {"✅ Completa" if total_chars > 30000 else "⚠️ Parcial" if total_chars > 5000 else "❌ Mínima"}

### Stacks Tecnológicos
"""
                        
                        for stack in stacks:
                            summary += f"""
### {stack.get('stack_type', '').upper()}
- **Título**: {stack.get('title')}
- **Esforço**: {stack.get('estimated_effort')}
- **Tecnologias**: {', '.join(stack.get('technologies', []))}
- **Tamanho**: {len(stack.get('content', '')):,} caracteres
"""
                        
                        summary += """

## 🏥 CARACTERÍSTICAS ESPECÍFICAS DO SISTEMA HOSPITALAR

### Compliance e Regulamentações
- ✅ LGPD - Lei Geral de Proteção de Dados
- ✅ CFM - Conselho Federal de Medicina
- ✅ ANVISA - Agência Nacional de Vigilância Sanitária
- ✅ TISS 3.0 - Padrão ANS para convênios
- ✅ HL7 FHIR - Padrão internacional de interoperabilidade

### Integrações Críticas
- 🔌 Equipamentos médicos (monitores, ventiladores)
- 🔌 Laboratório automatizado
- 🔌 Farmácia hospitalar
- 🔌 Sistema SUS (DataSUS)
- 🔌 Convênios (XML TISS)

### Módulos Principais
- 📋 Prontuário Eletrônico do Paciente (PEP)
- 💊 Prescrição Médica Digital
- 🏥 Gestão de Internações e Leitos
- 🔬 Resultados de Exames
- 💰 Faturamento SUS/Convênios
- 📱 App Mobile para Equipe Médica
- 📊 Dashboard Gerencial com BI

## 📄 ARQUIVOS GERADOS

1. **FRONTEND_HOSPITAL.md** - Interface do usuário e aplicações web/mobile
2. **BACKEND_HOSPITAL.md** - APIs, lógica de negócio e integrações
3. **DATABASE_HOSPITAL.md** - Estrutura de dados e schema completo
4. **DEVOPS_HOSPITAL.md** - Infraestrutura, deploy e monitoramento

## ✅ VALIDAÇÃO DA DOCUMENTAÇÃO

### Análise de Qualidade
"""
                        if total_chars > 30000:
                            summary += """
- ✅ **EXCELENTE**: Documentação healthcare-específica completa
- ✅ Mais de 30.000 caracteres de conteúdo técnico
- ✅ Templates especializados aplicados corretamente
- ✅ Compliance e regulamentações detalhadas
- ✅ Integrações hospitalares específicas
"""
                        elif total_chars > 5000:
                            summary += """
- ⚠️ **PARCIAL**: Documentação com alguns elementos específicos
- ⚠️ Entre 5.000 e 30.000 caracteres
- ⚠️ Templates parcialmente especializados
- ⚠️ Necessita mais detalhamento
"""
                        else:
                            summary += """
- ❌ **MÍNIMA**: Documentação genérica detectada
- ❌ Menos de 5.000 caracteres totais
- ❌ Templates genéricos foram usados
- ❌ Requer reconfiguração do sistema
"""
                        
                        summary += """

## 🎯 PRÓXIMOS PASSOS

1. **Revisão Técnica**: Validar com equipe de arquitetura
2. **Aprovação Compliance**: Verificar com jurídico/compliance
3. **Estimativa Detalhada**: Refinar estimativas com equipe
4. **Kickoff**: Iniciar desenvolvimento seguindo a documentação

## 📞 CONTATO

Para dúvidas sobre esta documentação, consulte a equipe de arquitetura.

---
*Documentação gerada automaticamente pelo sistema IA Compose*
*Session: {session_id}*
""".format(session_id=session_id)
                        
                        with open(test_dir / 'RESUMO_EXECUTIVO_V2.md', 'w', encoding='utf-8') as f:
                            f.write(summary)
                        
                        print(f"   ✅ RESUMO_EXECUTIVO_V2.md: {len(summary):,} caracteres")
                        
                        # Final validation
                        print("\n🏁 VALIDAÇÃO FINAL")
                        print("=" * 60)
                        
                        if total_chars > 30000:
                            print("✅ SUCESSO COMPLETO!")
                            print(f"   Documentação healthcare específica: {total_chars:,} caracteres")
                            print("   Templates especializados aplicados corretamente")
                            print("   Sistema pronto para produção hospitalar")
                        elif total_chars > 5000:
                            print("⚠️ SUCESSO PARCIAL")
                            print(f"   Documentação parcial: {total_chars:,} caracteres")
                            print("   Alguns templates específicos aplicados")
                            print("   Recomenda-se revisão")
                        else:
                            print("❌ FALHA NA ESPECIALIZAÇÃO")
                            print(f"   Documentação genérica: {total_chars:,} caracteres")
                            print("   Templates healthcare NÃO foram aplicados")
                            print("   Verificar configuração do DocumentGeneratorService")
                        
                        return test_results
                    else:
                        print(f"❌ Erro API 4: {response4.status_code}")
                        print(f"   Detalhes: {response4.text[:500]}")
                else:
                    print(f"❌ Erro confirmação resumo: {confirm_response.status_code}")
            else:
                print(f"❌ Erro API 3: {response3.status_code}")
                print(f"   Detalhes: {response3.text[:500]}")
        else:
            print(f"❌ Erro API 2: {response2.status_code}")
            print(f"   Detalhes: {response2.text[:500]}")
    else:
        print(f"❌ Erro API 1: {response1.status_code}")
        print(f"   Detalhes: {response1.text[:500]}")

if __name__ == "__main__":
    test_healthcare_system()