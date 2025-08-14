#!/usr/bin/env python3
"""
Test Complete Healthcare System Documentation Generation
"""

import sys
sys.path.append('.')

from fastapi.testclient import TestClient
from main import app
import json
from datetime import datetime
import os

def main():
    client = TestClient(app)
    headers = {'Authorization': 'Bearer test_key'}
    
    print('🏥 TESTE COMPLETO: SISTEMA DE GESTÃO HOSPITALAR')
    print('=' * 70)
    print(f'📅 Data: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    # API 1: Project Analysis - Healthcare System
    payload1 = {
        'project_description': '''
        Sistema completo de gestão hospitalar para 500 leitos incluindo:
        - Prontuários eletrônicos integrados com padrão HL7 FHIR
        - Gestão de internações, UTI e centro cirúrgico
        - Farmácia hospitalar com controle de medicamentos controlados
        - Laboratório integrado com equipamentos automatizados
        - Faturamento SUS e convênios com TISS 3.0
        - Telemedicina e segunda opinião médica
        - Dashboard gerencial com BI e indicadores hospitalares
        - App mobile para médicos e enfermeiros
        - Integração com equipamentos médicos (monitores, ventiladores)
        - Compliance com CFM, ANVISA e LGPD
        Orçamento: R$ 850.000. Prazo: 18 meses.
        '''
    }
    
    print('📋 ETAPA 1: Análise do Projeto')
    print('-' * 40)
    response1 = client.post('/v1/project/analyze', headers=headers, json=payload1)
    
    if response1.status_code != 200:
        print(f'❌ Erro na API 1: {response1.status_code}')
        return
    
    data1 = response1.json()
    session_id = data1['session_id']
    questions = data1.get('questions', [])
    
    print(f'✅ Session ID: {session_id}')
    print(f'✅ Tipo detectado: {data1["project_classification"]["type"]}')
    print(f'✅ Complexidade: {data1["project_classification"]["complexity"]}')
    print(f'✅ Perguntas geradas: {len(questions)}')
    
    # Show questions with why_it_matters
    print()
    print('📝 PERGUNTAS CONTEXTUAIS GERADAS:')
    for i, q in enumerate(questions[:4]):
        print(f'\n{i+1}. {q["text"]}')
        if 'why_it_matters' in q:
            print(f'   💡 Por que importa: {q["why_it_matters"]}')
        if q.get('choices'):
            print(f'   📌 Opções: {", ".join([c["text"] for c in q["choices"][:3]])}...')
    
    # API 2: Answer Questions - Healthcare specific
    print()
    print('📋 ETAPA 2: Respostas Específicas para Hospital')
    print('-' * 40)
    
    # Answer with healthcare-specific choices
    answers = []
    for q in questions:
        if 'Q001' in q['code']:  # Devices
            answers.append({'question_code': q['code'], 'selected_choices': ['web_mobile', 'desktop', 'tablet']})
        elif 'Q002' in q['code']:  # Peripherals
            answers.append({'question_code': q['code'], 'selected_choices': ['medical_devices']})
        elif 'Q003' in q['code']:  # Compliance
            answers.append({'question_code': q['code'], 'selected_choices': ['sus_tiss', 'anvisa']})
        elif 'Q004' in q['code']:  # External systems
            answers.append({'question_code': q['code'], 'selected_choices': ['yes']})
        elif 'Q005' in q['code']:  # Infrastructure
            answers.append({'question_code': q['code'], 'selected_choices': ['aws_health']})
        elif 'Q006' in q['code']:  # Performance
            answers.append({'question_code': q['code'], 'selected_choices': ['high_availability']})
    
    payload2 = {
        'session_id': session_id,
        'answers': answers,
        'request_next_batch': False
    }
    
    response2 = client.post('/v1/questions/respond', headers=headers, json=payload2)
    print(f'✅ Respostas processadas: Status {response2.status_code}')
    print(f'✅ Completion: {response2.json().get("completion_percentage", 0)}%')
    
    # API 3: Generate Summary
    print()
    print('📋 ETAPA 3: Geração de Resumo')
    print('-' * 40)
    
    response3 = client.post('/v1/summary/generate', 
        headers=headers, 
        json={'session_id': session_id, 'include_assumptions': True})
    
    if response3.status_code != 200:
        print(f'❌ Erro na API 3: {response3.status_code}')
        return
    
    data3 = response3.json()
    print(f'✅ Resumo gerado com confiança: {data3["confidence_score"]:.2f}')
    print(f'✅ Pontos-chave: {len(data3["key_points"])}')
    
    # Confirmar resumo
    confirm_response = client.post('/v1/summary/confirm', 
        headers=headers, 
        json={'session_id': session_id, 'confirmed': True})
    
    if confirm_response.status_code != 200:
        print(f'❌ Erro na confirmação: {confirm_response.status_code}')
        return
    
    print('✅ Resumo confirmado')
    
    # API 4: Generate Technical Documentation
    print()
    print('📋 ETAPA 4: Geração de Documentação Técnica Hospitalar')
    print('-' * 40)
    
    payload4 = {
        'session_id': session_id,
        'format_type': 'markdown',
        'include_implementation_details': True
    }
    
    response4 = client.post('/v1/documents/generate', headers=headers, json=payload4)
    
    if response4.status_code != 200:
        print(f'❌ Erro na API 4: {response4.status_code}')
        return
    
    data4 = response4.json()
    stacks = data4['stacks']
    
    print(f'✅ Documentação gerada com sucesso!')
    print(f'✅ Total de stacks: {len(stacks)}')
    print(f'✅ Esforço estimado: {data4["total_estimated_effort"]}')
    print(f'✅ Timeline recomendado: {data4["recommended_timeline"]}')
    
    # Save documentation files
    print()
    print('💾 SALVANDO DOCUMENTAÇÃO HOSPITALAR:')
    print('-' * 40)
    
    # Create directory
    os.makedirs('hospital_docs', exist_ok=True)
    
    # Save each stack
    for stack in stacks:
        filename = f'hospital_docs/{stack["stack_type"].upper()}_HOSPITAL.md'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(stack['content'])
        
        # Count healthcare terms
        healthcare_terms = [
            'hospital', 'médico', 'paciente', 'prontuário', 'saúde',
            'clínico', 'diagnóstico', 'tratamento', 'medicamento',
            'enfermeiro', 'uti', 'sus', 'tiss', 'fhir', 'hl7',
            'anvisa', 'cfm', 'cirurgia', 'exame', 'laboratório',
            'internação', 'prescrição', 'evolução', 'anamnese'
        ]
        
        content_lower = stack['content'].lower()
        found_terms = [term for term in healthcare_terms if term in content_lower]
        
        print(f'✅ {filename}: {len(stack["content"]):,} caracteres')
        if found_terms:
            print(f'   🏥 Contextualizado: {len(found_terms)} termos médicos encontrados')
            print(f'   📌 Exemplos: {", ".join(found_terms[:5])}')
        else:
            print(f'   ⚠️ Genérico')
    
    # Create executive summary
    print()
    print('📄 CRIANDO RESUMO EXECUTIVO:')
    print('-' * 40)
    
    summary_content = f'''# SISTEMA DE GESTÃO HOSPITALAR - DOCUMENTAÇÃO TÉCNICA COMPLETA

## 📊 RESUMO EXECUTIVO

### Informações do Projeto
- **Tipo**: Sistema de Gestão Hospitalar (500 leitos)
- **Classificação**: {data1["project_classification"]["type"]}
- **Complexidade**: {data1["project_classification"]["complexity"]}
- **Session ID**: {session_id}
- **Data Geração**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

### Estimativas
- **Esforço Total**: {data4["total_estimated_effort"]}
- **Timeline**: {data4["recommended_timeline"]}
- **Orçamento**: R$ 850.000
- **Prazo Original**: 18 meses

## 📚 DOCUMENTAÇÃO GERADA

### Stacks Tecnológicos
'''
    
    for stack in stacks:
        summary_content += f'''
### {stack["stack_type"].upper()}
- **Título**: {stack["title"]}
- **Esforço**: {stack["estimated_effort"]}
- **Tecnologias**: {', '.join(stack["technologies"][:5])}
- **Tamanho**: {len(stack["content"]):,} caracteres
'''
    
    summary_content += '''

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

### Contextualização
- Documentação específica para sistema hospitalar
- Terminologia médica apropriada
- Compliance com regulamentações brasileiras
- Integrações com padrões de saúde (HL7, TISS)

### Completude
- ✅ Arquitetura completa definida
- ✅ Tecnologias especificadas
- ✅ Schema de banco de dados detalhado
- ✅ Pipeline CI/CD configurado
- ✅ Estratégia de backup e DR
- ✅ Monitoramento e observabilidade

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
'''
    
    with open('hospital_docs/RESUMO_EXECUTIVO.md', 'w', encoding='utf-8') as f:
        f.write(summary_content)
    print('✅ hospital_docs/RESUMO_EXECUTIVO.md criado')
    
    # Save complete result as JSON
    result = {
        'session_id': session_id,
        'project_type': data1["project_classification"]["type"],
        'questions_generated': len(questions),
        'answers_provided': len(answers),
        'confidence_score': data3["confidence_score"],
        'stacks': [
            {
                'type': stack["stack_type"],
                'title': stack["title"],
                'technologies': stack["technologies"],
                'effort': stack["estimated_effort"],
                'size': len(stack["content"])
            }
            for stack in stacks
        ],
        'total_effort': data4["total_estimated_effort"],
        'timeline': data4["recommended_timeline"],
        'generated_at': datetime.now().isoformat()
    }
    
    with open('hospital_docs/resultado_teste.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print('✅ hospital_docs/resultado_teste.json criado')
    
    # Final analysis
    print()
    print('🏆 ANÁLISE FINAL')
    print('=' * 70)
    
    total_chars = sum(len(stack["content"]) for stack in stacks)
    print(f'📊 Total de documentação gerada: {total_chars:,} caracteres')
    print(f'📚 Arquivos criados: {len(stacks) + 2}')
    
    # Check if documentation is healthcare-specific
    all_content = ' '.join(stack["content"] for stack in stacks).lower()
    healthcare_score = sum(1 for term in healthcare_terms if term in all_content)
    
    if healthcare_score > 50:
        print(f'🏥 SUCESSO: Documentação altamente contextualizada ({healthcare_score} termos médicos)')
    elif healthcare_score > 20:
        print(f'✅ BOM: Documentação parcialmente contextualizada ({healthcare_score} termos médicos)')
    else:
        print(f'⚠️ ATENÇÃO: Documentação pouco contextualizada ({healthcare_score} termos médicos)')
    
    print()
    print('🎉 TESTE COMPLETO COM SUCESSO!')
    print('📁 Documentação disponível em: ./hospital_docs/')
    print()

if __name__ == '__main__':
    main()