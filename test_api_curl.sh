#!/bin/bash

# IA Compose API - Complete Test Suite with curl
# ================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:8001"
API_KEY="test_key"

# Function to print headers
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Function to print request
print_request() {
    echo -e "\n${YELLOW}REQUEST:${NC}"
    echo "$1"
}

# Function to print response
print_response() {
    echo -e "\n${GREEN}RESPONSE:${NC}"
    echo "$1" | python3 -m json.tool
}

# Start test report
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        IA COMPOSE API - COMPREHENSIVE TEST REPORT         ║${NC}"
echo -e "${BLUE}║                    CURL API TESTING                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "\nTest Date: $(date)"
echo -e "Base URL: $BASE_URL"
echo -e "API Key: $API_KEY"

# ================================================
# TEST 1: Health Check (No Auth Required)
# ================================================
print_header "TEST 1: Health Check Endpoint"
echo "Endpoint: GET /health"
echo "Description: Verify API is running"

REQUEST_CMD="curl -s -X GET $BASE_URL/health"
print_request "$REQUEST_CMD"

RESPONSE=$(eval $REQUEST_CMD)
print_response "$RESPONSE"

# ================================================
# TEST 2: API 1 - Project Analysis
# ================================================
print_header "TEST 2: API 1 - Project Analysis"
echo "Endpoint: POST /v1/project/analyze"
echo "Description: Analyze project description and generate questions"

PROJECT_JSON='{
  "project_description": "Sistema completo de gestão hospitalar para 500 leitos incluindo prontuários eletrônicos integrados com padrão HL7 FHIR, módulo de farmácia com controle automatizado de estoque, sistema de agendamento inteligente com IA para otimização de recursos, faturamento integrado com convênios, dashboard gerencial com indicadores em tempo real, módulo de telemedicina para consultas remotas, controle de leitos com mapa interativo, gestão de centro cirúrgico com checklist de segurança, módulo de laboratório com integração LIMS, e aplicativo móvel para médicos e enfermeiros. Prazo: 12 meses. Orçamento: R$ 3.500.000."
}'

REQUEST_CMD="curl -s -X POST $BASE_URL/v1/project/analyze \
  -H 'Authorization: Bearer $API_KEY' \
  -H 'Content-Type: application/json' \
  -d '$PROJECT_JSON'"

print_request "$REQUEST_CMD"

RESPONSE=$(curl -s -X POST $BASE_URL/v1/project/analyze \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PROJECT_JSON")

print_response "$RESPONSE"

# Extract session_id for next requests
SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', ''))")
echo -e "\n${GREEN}Session ID captured: $SESSION_ID${NC}"

# ================================================
# TEST 3: API 2 - Questions Response
# ================================================
print_header "TEST 3: API 2 - Questions Response"
echo "Endpoint: POST /v1/questions/respond"
echo "Description: Submit answers to generated questions"

ANSWERS_JSON='{
  "session_id": "'$SESSION_ID'",
  "answers": [
    {
      "question_code": "Q001",
      "selected_choices": ["web_app", "mobile_app"]
    },
    {
      "question_code": "Q002",
      "selected_choices": ["large"]
    },
    {
      "question_code": "Q003",
      "selected_choices": ["react", "nodejs", "postgresql"]
    },
    {
      "question_code": "Q004",
      "selected_choices": ["high_availability"]
    },
    {
      "question_code": "Q005",
      "selected_choices": ["cloud_aws"]
    }
  ],
  "request_next_batch": true
}'

REQUEST_CMD="curl -s -X POST $BASE_URL/v1/questions/respond \
  -H 'Authorization: Bearer $API_KEY' \
  -H 'Content-Type: application/json' \
  -d '$ANSWERS_JSON'"

print_request "$REQUEST_CMD"

RESPONSE=$(curl -s -X POST $BASE_URL/v1/questions/respond \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$ANSWERS_JSON")

print_response "$RESPONSE"

# ================================================
# TEST 4: API 3.1 - Summary Generation
# ================================================
print_header "TEST 4: API 3.1 - Summary Generation"
echo "Endpoint: POST /v1/summary/generate"
echo "Description: Generate project summary based on answers"

SUMMARY_REQUEST_JSON='{
  "session_id": "'$SESSION_ID'",
  "include_assumptions": true,
  "language": "pt-BR"
}'

REQUEST_CMD="curl -s -X POST $BASE_URL/v1/summary/generate \
  -H 'Authorization: Bearer $API_KEY' \
  -H 'Content-Type: application/json' \
  -d '$SUMMARY_REQUEST_JSON'"

print_request "$REQUEST_CMD"

RESPONSE=$(curl -s -X POST $BASE_URL/v1/summary/generate \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$SUMMARY_REQUEST_JSON")

print_response "$RESPONSE"

# ================================================
# TEST 5: API 3.2 - Summary Confirmation
# ================================================
print_header "TEST 5: API 3.2 - Summary Confirmation"
echo "Endpoint: POST /v1/summary/confirm"
echo "Description: Confirm or reject generated summary"

CONFIRM_JSON='{
  "session_id": "'$SESSION_ID'",
  "confirmed": true,
  "feedback": "Summary looks good, please proceed with document generation"
}'

REQUEST_CMD="curl -s -X POST $BASE_URL/v1/summary/confirm \
  -H 'Authorization: Bearer $API_KEY' \
  -H 'Content-Type: application/json' \
  -d '$CONFIRM_JSON'"

print_request "$REQUEST_CMD"

RESPONSE=$(curl -s -X POST $BASE_URL/v1/summary/confirm \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$CONFIRM_JSON")

print_response "$RESPONSE"

# ================================================
# TEST 6: API 4 - Document Generation
# ================================================
print_header "TEST 6: API 4 - Document Generation"
echo "Endpoint: POST /v1/documents/generate"
echo "Description: Generate technical documentation"

DOC_REQUEST_JSON='{
  "session_id": "'$SESSION_ID'",
  "format_type": "markdown",
  "include_implementation_details": true,
  "include_task_lists": true,
  "technical_depth": "detailed"
}'

REQUEST_CMD="curl -s -X POST $BASE_URL/v1/documents/generate \
  -H 'Authorization: Bearer $API_KEY' \
  -H 'Content-Type: application/json' \
  -d '$DOC_REQUEST_JSON'"

print_request "$REQUEST_CMD"

RESPONSE=$(curl -s -X POST $BASE_URL/v1/documents/generate \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$DOC_REQUEST_JSON")

print_response "$RESPONSE"

# ================================================
# TEST 7: Service Health Endpoints
# ================================================
print_header "TEST 7: Service Health Checks"
echo "Testing all service health endpoints"

echo -e "\n${YELLOW}7.1 - Question Engine Health:${NC}"
REQUEST_CMD="curl -s -X GET $BASE_URL/health/question-engine"
print_request "$REQUEST_CMD"
RESPONSE=$(eval $REQUEST_CMD)
print_response "$RESPONSE"

echo -e "\n${YELLOW}7.2 - Summary Engine Health:${NC}"
REQUEST_CMD="curl -s -X GET $BASE_URL/health/summary-engine"
print_request "$REQUEST_CMD"
RESPONSE=$(eval $REQUEST_CMD)
print_response "$RESPONSE"

echo -e "\n${YELLOW}7.3 - Document Generator Health:${NC}"
REQUEST_CMD="curl -s -X GET $BASE_URL/health/document-generator"
print_request "$REQUEST_CMD"
RESPONSE=$(eval $REQUEST_CMD)
print_response "$RESPONSE"

echo -e "\n${YELLOW}7.4 - Session Manager Health:${NC}"
REQUEST_CMD="curl -s -X GET $BASE_URL/health/session-manager"
print_request "$REQUEST_CMD"
RESPONSE=$(eval $REQUEST_CMD)
print_response "$RESPONSE"

# ================================================
# TEST 8: Error Handling Tests
# ================================================
print_header "TEST 8: Error Handling Tests"

echo -e "\n${YELLOW}8.1 - Missing API Key (401):${NC}"
REQUEST_CMD="curl -s -X POST $BASE_URL/v1/project/analyze \
  -H 'Content-Type: application/json' \
  -d '{\"project_description\": \"test\"}'"
print_request "$REQUEST_CMD"
RESPONSE=$(curl -s -X POST $BASE_URL/v1/project/analyze \
  -H "Content-Type: application/json" \
  -d '{"project_description": "test"}')
print_response "$RESPONSE"

echo -e "\n${YELLOW}8.2 - Invalid API Key (401):${NC}"
REQUEST_CMD="curl -s -X POST $BASE_URL/v1/project/analyze \
  -H 'Authorization: Bearer invalid_key' \
  -H 'Content-Type: application/json' \
  -d '{\"project_description\": \"test\"}'"
print_request "$REQUEST_CMD"
RESPONSE=$(curl -s -X POST $BASE_URL/v1/project/analyze \
  -H "Authorization: Bearer invalid_key" \
  -H "Content-Type: application/json" \
  -d '{"project_description": "test"}')
print_response "$RESPONSE"

echo -e "\n${YELLOW}8.3 - Too Short Description (422):${NC}"
REQUEST_CMD="curl -s -X POST $BASE_URL/v1/project/analyze \
  -H 'Authorization: Bearer $API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{\"project_description\": \"abc\"}'"
print_request "$REQUEST_CMD"
RESPONSE=$(curl -s -X POST $BASE_URL/v1/project/analyze \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"project_description": "abc"}')
print_response "$RESPONSE"

# ================================================
# TEST 9: Complete Workflow Test
# ================================================
print_header "TEST 9: Complete End-to-End Workflow"
echo "Testing complete flow from project analysis to document generation"

echo -e "\n${YELLOW}Step 1: Create new project${NC}"
PROJECT_JSON='{
  "project_description": "Marketplace B2B para indústria farmacêutica conectando laboratórios, distribuidores e farmácias. Sistema com catálogo de 50.000 produtos, gestão de pedidos em lote, sistema de cotações, EDI para integração com ERPs, controle de lotes e validades, rastreabilidade ANVISA, sistema de crédito e cobrança, dashboard analytics com BI, app mobile para representantes. Compliance com RDC 320/2019. Prazo: 8 meses. Budget: R$ 1.800.000."
}'

RESPONSE=$(curl -s -X POST $BASE_URL/v1/project/analyze \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PROJECT_JSON")

SESSION_ID_2=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', ''))")
echo "New Session ID: $SESSION_ID_2"
echo "Questions generated: $(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_questions', 0))")"

echo -e "\n${YELLOW}Step 2: Answer questions${NC}"
ANSWERS_JSON='{
  "session_id": "'$SESSION_ID_2'",
  "answers": [
    {"question_code": "Q001", "selected_choices": ["web_app"]},
    {"question_code": "Q002", "selected_choices": ["large"]},
    {"question_code": "Q003", "selected_choices": ["python", "react", "postgresql"]}
  ],
  "request_next_batch": false
}'

RESPONSE=$(curl -s -X POST $BASE_URL/v1/questions/respond \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$ANSWERS_JSON")
echo "Completion: $(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('completion_percentage', 0))")%"

echo -e "\n${YELLOW}Step 3: Generate summary${NC}"
RESPONSE=$(curl -s -X POST $BASE_URL/v1/summary/generate \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID_2\", \"include_assumptions\": true}")
echo "Summary confidence: $(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('confidence_score', 0))")"

echo -e "\n${YELLOW}Step 4: Confirm summary${NC}"
RESPONSE=$(curl -s -X POST $BASE_URL/v1/summary/confirm \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID_2\", \"confirmed\": true}")
echo "Confirmation status: $(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")"

echo -e "\n${YELLOW}Step 5: Generate documents${NC}"
RESPONSE=$(curl -s -X POST $BASE_URL/v1/documents/generate \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID_2\", \"format_type\": \"markdown\"}")
echo "Documents generated: $(echo "$RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('stacks', [])))")"
echo "Total effort: $(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_estimated_effort', 'N/A'))")"

# ================================================
# FINAL REPORT
# ================================================
print_header "TEST SUMMARY REPORT"

echo -e "${GREEN}✅ Test Suite Completed${NC}"
echo -e "\nTests Executed:"
echo "  1. Health Check - No Auth Required"
echo "  2. Project Analysis API"
echo "  3. Questions Response API"
echo "  4. Summary Generation API"
echo "  5. Summary Confirmation API"
echo "  6. Document Generation API"
echo "  7. Service Health Endpoints (4 services)"
echo "  8. Error Handling (3 scenarios)"
echo "  9. Complete End-to-End Workflow"

echo -e "\n${GREEN}Total API Calls: 18${NC}"
echo -e "${GREEN}Session IDs Generated: 2${NC}"

echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                  TEST EXECUTION COMPLETED                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"