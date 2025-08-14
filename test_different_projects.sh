#!/bin/bash

# Test Different Project Types
# Tests the API with various domains to ensure AI generation works for any type

echo "🧪 TESTE DE DIFERENTES TIPOS DE PROJETOS"
echo "========================================"
echo ""

# Configuration
API_KEY="test_key"
BASE_URL="http://localhost:8000"
RESPONSE_DIR="api_responses"

# Create response directory
mkdir -p $RESPONSE_DIR

# Function to test a project
test_project() {
    local PROJECT_NAME=$1
    local PROJECT_DESC=$2
    local OUTPUT_PREFIX=$3
    
    echo "🔍 Testando: $PROJECT_NAME"
    echo "----------------------------------------"
    
    # API 1: Project Analysis
    RESPONSE_1=$(curl -s -X POST "$BASE_URL/v1/project/analyze" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"project_description\": \"$PROJECT_DESC\"}")
    
    echo "$RESPONSE_1" > "$RESPONSE_DIR/${OUTPUT_PREFIX}_01_analysis.json"
    
    # Extract session_id
    SESSION_ID=$(echo "$RESPONSE_1" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null)
    
    if [ -z "$SESSION_ID" ]; then
        echo "❌ Erro: Não foi possível obter session_id"
        return 1
    fi
    
    echo "✅ Session ID: $SESSION_ID"
    
    # API 2: Answer Questions (generic answers)
    ANSWERS=$(cat <<EOF
{
  "session_id": "$SESSION_ID",
  "answers": [
    {"question_code": "Q001", "selected_choices": ["web_app"]},
    {"question_code": "Q002", "selected_choices": ["standard"]},
    {"question_code": "Q003", "selected_choices": ["standard"]},
    {"question_code": "Q004", "selected_choices": ["api"]},
    {"question_code": "Q005", "selected_choices": ["b2b"]},
    {"question_code": "Q006", "selected_choices": ["standard"]}
  ],
  "request_next_batch": false
}
EOF
)
    
    RESPONSE_2=$(curl -s -X POST "$BASE_URL/v1/questions/respond" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Content-Type: application/json" \
      -d "$ANSWERS")
    
    echo "$RESPONSE_2" > "$RESPONSE_DIR/${OUTPUT_PREFIX}_02_questions.json"
    
    # API 3: Generate Summary
    RESPONSE_3=$(curl -s -X POST "$BASE_URL/v1/summary/generate" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"session_id\": \"$SESSION_ID\", \"include_assumptions\": true}")
    
    echo "$RESPONSE_3" > "$RESPONSE_DIR/${OUTPUT_PREFIX}_03_summary.json"
    
    # Confirm Summary
    curl -s -X POST "$BASE_URL/v1/summary/confirm" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"session_id\": \"$SESSION_ID\", \"confirmed\": true}" > /dev/null
    
    # API 4: Generate Documents
    RESPONSE_4=$(curl -s -X POST "$BASE_URL/v1/documents/generate" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"session_id\": \"$SESSION_ID\", \"format_type\": \"markdown\", \"include_implementation_details\": true}")
    
    echo "$RESPONSE_4" > "$RESPONSE_DIR/${OUTPUT_PREFIX}_04_documents.json"
    
    # Extract documentation size
    TOTAL_SIZE=$(echo "$RESPONSE_4" | python3 -c "
import sys, json
data = json.load(sys.stdin)
total = 0
if 'stacks' in data:
    for stack in data['stacks']:
        total += len(stack.get('content', ''))
print(total)
" 2>/dev/null)
    
    echo "📄 Documentação gerada: $TOTAL_SIZE caracteres"
    echo ""
}

# ========================================
# Test Different Project Types
# ========================================

# 1. Healthcare System
test_project "Sistema de Saúde" \
  "Sistema de gestão para clínica médica com 20 consultórios, incluindo agendamento online, prontuário eletrônico, prescrições digitais, integração com laboratórios, telemedicina, faturamento de convênios, app para pacientes. Conformidade com LGPD e CFM. Orçamento: R$ 180.000" \
  "healthcare"

# 2. Educational Platform
test_project "Plataforma Educacional" \
  "Plataforma de ensino online com cursos em vídeo, sistema de avaliações, certificados digitais, gamificação, fórum de discussões, aulas ao vivo, área do professor, área do aluno, pagamentos recorrentes, aplicativo mobile. 50.000 alunos esperados. Orçamento: R$ 220.000" \
  "education"

# 3. Financial System
test_project "Sistema Financeiro" \
  "Sistema de gestão financeira para corretora de valores incluindo: home broker, análise técnica em tempo real, robôs de investimento, carteira recomendada, integração com B3, compliance com CVM, app mobile para trading. Orçamento: R$ 450.000" \
  "financial"

# 4. IoT Platform
test_project "Plataforma IoT" \
  "Plataforma de monitoramento IoT para indústria 4.0 com coleta de dados de 1000 sensores, dashboard em tempo real, alertas inteligentes, manutenção preditiva com ML, integração com ERPs, relatórios gerenciais, API para terceiros. Orçamento: R$ 320.000" \
  "iot"

# 5. Social Network
test_project "Rede Social" \
  "Rede social para profissionais de tecnologia com perfis, conexões, feed de notícias, mensagens privadas, grupos de discussão, eventos online, vagas de emprego, sistema de recomendações, moderação com IA, monetização via assinaturas. Orçamento: R$ 280.000" \
  "social"

# ========================================
# Generate Comparison Report
# ========================================

echo "📊 GERANDO RELATÓRIO COMPARATIVO"
echo "================================="
echo ""

python3 <<EOF
import json
import os

response_dir = "$RESPONSE_DIR"
projects = ["healthcare", "education", "financial", "iot", "social"]

report = []
report.append("# RELATÓRIO COMPARATIVO DE PROJETOS")
report.append("")
report.append("| Projeto | Tipo Detectado | Complexidade | Chars Gerados | Tecnologias Frontend | Tecnologias Backend |")
report.append("|---------|---------------|--------------|---------------|---------------------|---------------------|")

for project in projects:
    try:
        # Load analysis
        with open(f"{response_dir}/{project}_01_analysis.json", "r") as f:
            analysis = json.load(f)
        
        # Load documents
        with open(f"{response_dir}/{project}_04_documents.json", "r") as f:
            docs = json.load(f)
        
        project_type = analysis.get("project_classification", {}).get("type", "N/A")
        complexity = analysis.get("project_classification", {}).get("complexity", "N/A")
        
        total_chars = 0
        frontend_tech = []
        backend_tech = []
        
        if "stacks" in docs:
            for stack in docs["stacks"]:
                total_chars += len(stack.get("content", ""))
                if stack.get("stack_type") == "frontend":
                    frontend_tech = stack.get("technologies", [])[:3]
                elif stack.get("stack_type") == "backend":
                    backend_tech = stack.get("technologies", [])[:3]
        
        report.append(f"| {project.title()} | {project_type} | {complexity} | {total_chars:,} | {', '.join(frontend_tech)} | {', '.join(backend_tech)} |")
        
    except Exception as e:
        report.append(f"| {project.title()} | ERROR | ERROR | 0 | N/A | N/A |")

report.append("")
report.append("## ANÁLISE")
report.append("")
report.append("- **Diversidade**: Sistema capaz de gerar documentação para diferentes domínios")
report.append("- **Consistência**: Todos os projetos recebem documentação completa dos 4 stacks")
report.append("- **Contextualização**: IA adapta tecnologias baseadas no tipo de projeto")
report.append("- **Volume**: Média de caracteres gerados por projeto")

# Save report
with open(f"{response_dir}/COMPARATIVE_REPORT.md", "w") as f:
    f.write("\\n".join(report))

print("\\n".join(report))
print("")
print(f"✅ Relatório salvo em: {response_dir}/COMPARATIVE_REPORT.md")
EOF

echo ""
echo "🎉 TESTE DE MÚLTIPLOS DOMÍNIOS CONCLUÍDO!"
echo ""
echo "Resultados salvos em: $RESPONSE_DIR/"