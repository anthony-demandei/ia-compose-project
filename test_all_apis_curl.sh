#!/bin/bash

# Test Script for All 4 APIs using curl
# Saves responses to files for analysis

echo "🧪 TESTE COMPLETO DAS 4 APIs COM CURL"
echo "======================================"
echo "Data: $(date)"
echo ""

# Configuration
API_KEY="test_key"
BASE_URL="http://localhost:8000"
RESPONSE_DIR="api_responses"

# Create response directory
mkdir -p $RESPONSE_DIR

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 PROJETO DE TESTE: Sistema de E-commerce${NC}"
echo ""

# Project description for testing
PROJECT_DESC=$(cat <<EOF
{
  "project_description": "Sistema completo de e-commerce para venda de produtos eletrônicos incluindo: catálogo com 10.000 produtos, carrinho de compras, múltiplas formas de pagamento (PIX, cartão, boleto), integração com correios para cálculo de frete, sistema de avaliações e reviews, programa de fidelidade com pontos, dashboard administrativo para gestão de vendas e estoque, relatórios gerenciais, integração com marketplaces (Mercado Livre, Amazon), sistema de cupons de desconto. Orçamento: R$ 250.000. Prazo: 8 meses."
}
EOF
)

# ========================================
# API 1: Project Analysis
# ========================================
echo -e "${GREEN}🔍 API 1: Análise do Projeto${NC}"
echo "Endpoint: POST /v1/project/analyze"
echo ""

RESPONSE_1=$(curl -s -X POST "$BASE_URL/v1/project/analyze" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PROJECT_DESC")

echo "$RESPONSE_1" > "$RESPONSE_DIR/01_project_analysis.json"
echo "$RESPONSE_1" | python3 -m json.tool

# Extract session_id
SESSION_ID=$(echo "$RESPONSE_1" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null)

if [ -z "$SESSION_ID" ]; then
    echo -e "${RED}❌ Erro: Não foi possível obter session_id${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Session ID: $SESSION_ID${NC}"
echo ""

# Extract questions for answering
QUESTIONS=$(echo "$RESPONSE_1" | python3 -c "import sys, json; data = json.load(sys.stdin); print(json.dumps(data.get('questions', [])))")

# ========================================
# API 2: Questions Response
# ========================================
echo -e "${GREEN}❓ API 2: Respondendo Perguntas${NC}"
echo "Endpoint: POST /v1/questions/respond"
echo ""

# Build answers based on questions
ANSWERS=$(cat <<EOF
{
  "session_id": "$SESSION_ID",
  "answers": [
    {
      "question_code": "Q001",
      "selected_choices": ["desktop_web", "mobile_responsive"]
    },
    {
      "question_code": "Q002",
      "selected_choices": ["payment_gateway", "shipping_api", "marketplace_integration"]
    },
    {
      "question_code": "Q003",
      "selected_choices": ["lgpd", "pci_dss"]
    },
    {
      "question_code": "Q004",
      "selected_choices": ["mercadolivre", "amazon", "correios"]
    },
    {
      "question_code": "Q005",
      "selected_choices": ["b2c"]
    },
    {
      "question_code": "Q006",
      "selected_choices": ["high_performance"]
    }
  ],
  "request_next_batch": false
}
EOF
)

RESPONSE_2=$(curl -s -X POST "$BASE_URL/v1/questions/respond" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$ANSWERS")

echo "$RESPONSE_2" > "$RESPONSE_DIR/02_questions_response.json"
echo "$RESPONSE_2" | python3 -m json.tool

echo ""

# ========================================
# API 3: Summary Generation
# ========================================
echo -e "${GREEN}📝 API 3: Geração do Resumo${NC}"
echo "Endpoint: POST /v1/summary/generate"
echo ""

SUMMARY_REQUEST=$(cat <<EOF
{
  "session_id": "$SESSION_ID",
  "include_assumptions": true
}
EOF
)

RESPONSE_3=$(curl -s -X POST "$BASE_URL/v1/summary/generate" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$SUMMARY_REQUEST")

echo "$RESPONSE_3" > "$RESPONSE_DIR/03_summary_generation.json"
echo "$RESPONSE_3" | python3 -m json.tool

echo ""

# Confirm summary
echo -e "${GREEN}✅ Confirmando Resumo${NC}"
echo "Endpoint: POST /v1/summary/confirm"
echo ""

CONFIRM_REQUEST=$(cat <<EOF
{
  "session_id": "$SESSION_ID",
  "confirmed": true
}
EOF
)

RESPONSE_3B=$(curl -s -X POST "$BASE_URL/v1/summary/confirm" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$CONFIRM_REQUEST")

echo "$RESPONSE_3B" > "$RESPONSE_DIR/03b_summary_confirm.json"
echo "$RESPONSE_3B" | python3 -m json.tool

echo ""

# ========================================
# API 4: Document Generation
# ========================================
echo -e "${GREEN}📄 API 4: Geração de Documentação${NC}"
echo "Endpoint: POST /v1/documents/generate"
echo ""

DOCUMENT_REQUEST=$(cat <<EOF
{
  "session_id": "$SESSION_ID",
  "format_type": "markdown",
  "include_implementation_details": true
}
EOF
)

RESPONSE_4=$(curl -s -X POST "$BASE_URL/v1/documents/generate" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$DOCUMENT_REQUEST")

echo "$RESPONSE_4" > "$RESPONSE_DIR/04_document_generation.json"

# Pretty print just the structure (not full content)
echo "$RESPONSE_4" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'stacks' in data:
    for stack in data['stacks']:
        print(f\"\\n📚 {stack.get('stack_type', '').upper()}:\")
        print(f\"   Title: {stack.get('title', '')}\")
        print(f\"   Technologies: {', '.join(stack.get('technologies', []))}\")
        print(f\"   Effort: {stack.get('estimated_effort', '')}\")
        print(f\"   Content Size: {len(stack.get('content', ''))} chars\")
    print(f\"\\n⏱️ Total Effort: {data.get('total_estimated_effort', '')}\")
    print(f\"📅 Timeline: {data.get('recommended_timeline', '')}\")
"

echo ""

# ========================================
# Final Report
# ========================================
echo -e "${YELLOW}📊 RELATÓRIO FINAL${NC}"
echo "=================="
echo ""

# Calculate total response sizes
for file in $RESPONSE_DIR/*.json; do
    SIZE=$(wc -c < "$file")
    FILENAME=$(basename "$file")
    echo "✅ $FILENAME: $SIZE bytes"
done

echo ""
echo -e "${GREEN}✅ Todas as respostas salvas em: $RESPONSE_DIR/${NC}"
echo ""

# Extract and save documentation content to separate files
echo -e "${YELLOW}📄 Extraindo documentação para arquivos separados...${NC}"

python3 <<EOF
import json
import os

response_dir = "$RESPONSE_DIR"

# Load the document generation response
with open(f"{response_dir}/04_document_generation.json", "r") as f:
    data = json.load(f)

if "stacks" in data:
    for stack in data["stacks"]:
        stack_type = stack.get("stack_type", "unknown")
        content = stack.get("content", "")
        
        # Save each stack's documentation to a separate file
        filename = f"{response_dir}/{stack_type}_documentation.md"
        with open(filename, "w") as f:
            f.write(content)
        
        print(f"✅ {stack_type}_documentation.md: {len(content)} chars")

# Create combined documentation file
combined_file = f"{response_dir}/COMPLETE_DOCUMENTATION.md"
with open(combined_file, "w") as f:
    f.write("# DOCUMENTAÇÃO TÉCNICA COMPLETA\\n")
    f.write(f"## Session: {data.get('session_id', '')}\\n")
    f.write(f"## Generated: {data.get('generated_at', '')}\\n\\n")
    
    if "stacks" in data:
        for stack in data["stacks"]:
            f.write(f"\\n\\n{'='*60}\\n")
            f.write(f"# {stack.get('title', '')}\\n")
            f.write(f"{'='*60}\\n\\n")
            f.write(stack.get('content', ''))
            f.write(f"\\n\\n**Technologies:** {', '.join(stack.get('technologies', []))}\\n")
            f.write(f"**Estimated Effort:** {stack.get('estimated_effort', '')}\\n")

print(f"\\n✅ COMPLETE_DOCUMENTATION.md created with all stacks")
EOF

echo ""
echo -e "${GREEN}🎉 TESTE COMPLETO FINALIZADO!${NC}"
echo ""
echo "Para ver a documentação completa:"
echo "  cat $RESPONSE_DIR/COMPLETE_DOCUMENTATION.md"
echo ""
echo "Para ver uma stack específica:"
echo "  cat $RESPONSE_DIR/frontend_documentation.md"
echo "  cat $RESPONSE_DIR/backend_documentation.md"
echo "  cat $RESPONSE_DIR/database_documentation.md"
echo "  cat $RESPONSE_DIR/devops_documentation.md"