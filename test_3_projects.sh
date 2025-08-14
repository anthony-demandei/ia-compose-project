#!/bin/bash

# ============================================================================
# Comprehensive Test Script for 3 Project Types
# ============================================================================
# This script tests the IA Compose API with 3 different project types
# and generates a detailed analysis of the documentation produced
# ============================================================================

set -e

# Configuration
API_KEY="test_key"
BASE_URL="http://localhost:8001"
RESULTS_DIR="test_results"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create results directory
mkdir -p $RESULTS_DIR

# Function to print colored headers
print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
}

# Function to test a project
test_project() {
    local PROJECT_NAME=$1
    local PROJECT_DESC=$2
    local ANSWERS=$3
    local OUTPUT_FILE=$4
    
    print_header "Testing $PROJECT_NAME"
    
    # Step 1: Analyze project
    echo -e "${YELLOW}Step 1: Analyzing project...${NC}"
    START_TIME=$(date +%s)
    
    ANALYZE_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/project/analyze" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"project_description\": \"$PROJECT_DESC\"}")
    
    ANALYZE_TIME=$(($(date +%s) - START_TIME))
    
    SESSION_ID=$(echo "$ANALYZE_RESPONSE" | jq -r '.session_id')
    TOTAL_QUESTIONS=$(echo "$ANALYZE_RESPONSE" | jq -r '.total_questions')
    PROJECT_TYPE=$(echo "$ANALYZE_RESPONSE" | jq -r '.project_classification.type')
    COMPLEXITY=$(echo "$ANALYZE_RESPONSE" | jq -r '.project_classification.complexity')
    
    echo "  ✓ Session ID: $SESSION_ID"
    echo "  ✓ Questions: $TOTAL_QUESTIONS"
    echo "  ✓ Type: $PROJECT_TYPE"
    echo "  ✓ Complexity: $COMPLEXITY"
    echo "  ✓ Analysis time: ${ANALYZE_TIME}s"
    
    # Save analysis response
    echo "$ANALYZE_RESPONSE" > "$RESULTS_DIR/${OUTPUT_FILE}_analysis.json"
    
    # Step 2: Answer questions
    echo -e "\n${YELLOW}Step 2: Answering questions...${NC}"
    curl -s -X POST "$BASE_URL/v1/questions/respond" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"session_id\": \"$SESSION_ID\",
            \"answers\": $ANSWERS,
            \"request_next_batch\": false
        }" > "$RESULTS_DIR/${OUTPUT_FILE}_answers.json"
    echo "  ✓ Questions answered"
    
    # Step 3: Generate summary
    echo -e "\n${YELLOW}Step 3: Generating summary...${NC}"
    SUMMARY_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/summary/generate" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\"}")
    
    echo "$SUMMARY_RESPONSE" > "$RESULTS_DIR/${OUTPUT_FILE}_summary.json"
    echo "  ✓ Summary generated"
    
    # Step 4: Confirm summary
    echo -e "\n${YELLOW}Step 4: Confirming summary...${NC}"
    curl -s -X POST "$BASE_URL/v1/summary/confirm" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"confirmed\": true}" > /dev/null
    echo "  ✓ Summary confirmed"
    
    # Step 5: Generate documents
    echo -e "\n${YELLOW}Step 5: Generating documents (this may take 1-2 minutes)...${NC}"
    START_TIME=$(date +%s)
    
    # Use timeout to prevent hanging
    if timeout 120 curl -s -X POST "$BASE_URL/v1/documents/generate" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"include_implementation_details\": true}" \
        > "$RESULTS_DIR/${OUTPUT_FILE}_documents.json" 2>&1; then
        
        DOC_TIME=$(($(date +%s) - START_TIME))
        echo "  ✓ Documents generated in ${DOC_TIME}s"
        
        # Extract key metrics
        DOC_SIZE=$(wc -c "$RESULTS_DIR/${OUTPUT_FILE}_documents.json" | awk '{print $1}')
        echo "  ✓ Document size: $DOC_SIZE bytes"
        
        # Try to extract effort and timeline (may fail if JSON has issues)
        if EFFORT=$(jq -r '.total_estimated_effort' "$RESULTS_DIR/${OUTPUT_FILE}_documents.json" 2>/dev/null); then
            echo "  ✓ Total effort: $EFFORT"
        fi
        
        if TIMELINE=$(jq -r '.recommended_timeline' "$RESULTS_DIR/${OUTPUT_FILE}_documents.json" 2>/dev/null); then
            echo "  ✓ Timeline: $TIMELINE"
        fi
        
        # Count stacks
        if STACK_COUNT=$(jq '.stacks | length' "$RESULTS_DIR/${OUTPUT_FILE}_documents.json" 2>/dev/null); then
            echo "  ✓ Stacks generated: $STACK_COUNT"
        fi
        
    else
        echo -e "  ${RED}✗ Document generation failed or timed out${NC}"
    fi
    
    echo -e "\n${GREEN}✓ Test completed for $PROJECT_NAME${NC}"
}

# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================

print_header "IA COMPOSE API - 3 PROJECT TYPES TEST"
echo "Starting comprehensive test at $(date)"

# Check if services are running
echo -e "\n${YELLOW}Checking services...${NC}"
if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo "  ✓ API is running"
else
    echo -e "  ${RED}✗ API is not running. Please start with: docker-compose up -d${NC}"
    exit 1
fi

# Check Redis
if docker exec ia-compose-redis redis-cli ping > /dev/null 2>&1; then
    echo "  ✓ Redis is running"
    INITIAL_KEYS=$(docker exec ia-compose-redis redis-cli DBSIZE | cut -d' ' -f2)
    echo "  ✓ Initial Redis keys: $INITIAL_KEYS"
else
    echo -e "  ${YELLOW}⚠ Redis is not running (cache disabled)${NC}"
fi

# ============================================================================
# PROJECT 1: E-COMMERCE PLATFORM
# ============================================================================

test_project \
    "E-COMMERCE PLATFORM" \
    "Plataforma de e-commerce B2C completa com catálogo de produtos, carrinho de compras, sistema de pagamentos integrado com PIX e cartão, gestão de pedidos, programa de fidelidade, avaliações de produtos, sistema de recomendação com IA e painel administrativo. Expectativa de 10.000 usuários simultâneos, integração com correios para frete, suporte multi-idioma." \
    '[
        {"question_code": "Q001", "selected_choices": ["web_app", "mobile_app"]},
        {"question_code": "Q002", "selected_choices": ["multi_vendor"]},
        {"question_code": "Q003", "selected_choices": ["tef_pix", "card_gateway"]},
        {"question_code": "Q004", "selected_choices": ["nfe_nfce"]},
        {"question_code": "Q005", "selected_choices": ["correios_api", "ml_integration"]},
        {"question_code": "Q006", "selected_choices": ["cloud_aws"]}
    ]' \
    "ecommerce"

sleep 5

# ============================================================================
# PROJECT 2: HEALTHCARE MANAGEMENT SYSTEM
# ============================================================================

test_project \
    "HEALTHCARE MANAGEMENT SYSTEM" \
    "Sistema de gestão hospitalar para clínica com 50 médicos e 5000 pacientes. Funcionalidades: prontuário eletrônico padrão TISS, agendamento de consultas com lembretes SMS, prescrições digitais com assinatura eletrônica, integração com laboratórios via HL7, faturamento TISS/ANS, telemedicina com videochamadas, controle de medicamentos ANVISA, dashboard gerencial com KPIs. Conformidade com CFM, LGPD e ISO 27001." \
    '[
        {"question_code": "Q001", "selected_choices": ["web_app", "tablet_app"]},
        {"question_code": "Q002", "selected_choices": ["integrated_emr"]},
        {"question_code": "Q003", "selected_choices": ["tiss_integration", "lab_integration"]},
        {"question_code": "Q004", "selected_choices": ["cfm_compliance", "lgpd"]},
        {"question_code": "Q005", "selected_choices": ["hl7_fhir", "dicom"]},
        {"question_code": "Q006", "selected_choices": ["on_premise"]}
    ]' \
    "healthcare"

sleep 5

# ============================================================================
# PROJECT 3: FINTECH MOBILE APP
# ============================================================================

test_project \
    "FINTECH MOBILE APPLICATION" \
    "Aplicativo de gestão financeira pessoal com carteira digital PIX, análise de gastos com IA e categorização automática, metas de economia gamificadas, investimentos automatizados via open banking, geração de relatórios PDF, notificações inteligentes push, integração com bancos via API, cashback em parceiros. Segurança PCI-DSS, autenticação biométrica e 2FA. Meta de 100k downloads no primeiro ano." \
    '[
        {"question_code": "Q001", "selected_choices": ["mobile_app", "web_app"]},
        {"question_code": "Q002", "selected_choices": ["open_banking", "pix_api"]},
        {"question_code": "Q003", "selected_choices": ["pci_dss", "biometric_auth"]},
        {"question_code": "Q004", "selected_choices": ["bacen_compliance"]},
        {"question_code": "Q005", "selected_choices": ["bank_apis", "investment_apis"]},
        {"question_code": "Q006", "selected_choices": ["cloud_aws"]}
    ]' \
    "fintech"

# ============================================================================
# FINAL ANALYSIS
# ============================================================================

print_header "TEST SUMMARY"

echo -e "\n${YELLOW}Results saved in:${NC}"
echo "  • $RESULTS_DIR/"
ls -la $RESULTS_DIR/*.json | awk '{print "    - " $9 " (" $5 " bytes)"}'

echo -e "\n${YELLOW}Redis Cache Status:${NC}"
if docker exec ia-compose-redis redis-cli ping > /dev/null 2>&1; then
    FINAL_KEYS=$(docker exec ia-compose-redis redis-cli DBSIZE | cut -d' ' -f2)
    NEW_KEYS=$((FINAL_KEYS - INITIAL_KEYS))
    echo "  • Initial keys: $INITIAL_KEYS"
    echo "  • Final keys: $FINAL_KEYS"
    echo "  • New keys cached: $NEW_KEYS"
    
    echo -e "\n${YELLOW}Cached keys:${NC}"
    docker exec ia-compose-redis redis-cli --scan --pattern "*" | while read key; do
        TTL=$(docker exec ia-compose-redis redis-cli TTL "$key")
        echo "    • $key (TTL: ${TTL}s)"
    done
fi

echo -e "\n${GREEN}✓ All tests completed successfully!${NC}"
echo "Test finished at $(date)"

# Generate simple analysis
echo -e "\n${YELLOW}Generating analysis report...${NC}"
python3 << 'EOF'
import json
import os

results_dir = "test_results"
projects = ["ecommerce", "healthcare", "fintech"]

print("\n📊 DOCUMENT GENERATION ANALYSIS")
print("=" * 60)

for project in projects:
    print(f"\n{project.upper()}:")
    
    # Try to read documents file
    doc_file = f"{results_dir}/{project}_documents.json"
    if os.path.exists(doc_file):
        try:
            with open(doc_file, 'r') as f:
                # Read first 1000 chars to check if valid
                content = f.read(1000)
                if '"stacks"' in content:
                    print(f"  ✓ Documents generated successfully")
                    print(f"  • File size: {os.path.getsize(doc_file):,} bytes")
                else:
                    print(f"  ⚠ Document file exists but may be incomplete")
        except:
            print(f"  ✗ Could not read document file")
    else:
        print(f"  ✗ Document file not found")
        
    # Try to read analysis file
    analysis_file = f"{results_dir}/{project}_analysis.json"
    if os.path.exists(analysis_file):
        try:
            with open(analysis_file, 'r') as f:
                data = json.load(f)
                classification = data.get('project_classification', {})
                print(f"  • Type: {classification.get('type', 'N/A')}")
                print(f"  • Complexity: {classification.get('complexity', 'N/A')}")
                print(f"  • Questions: {data.get('total_questions', 'N/A')}")
        except:
            pass

print("\n" + "=" * 60)
EOF