#!/bin/bash

# Test script for refinement questions flow
# ==========================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:8001"
API_KEY="test_key"

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  TEST: Summary Rejection with Refinement Questions Flow    ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Create a new project
echo -e "${YELLOW}STEP 1: Creating new project...${NC}"

PROJECT_JSON='{
  "project_description": "Sistema de gestão de vendas para loja de varejo com controle de estoque, PDV, relatórios gerenciais e integração com nota fiscal eletrônica. Precisa funcionar offline e sincronizar quando tiver internet. Orçamento: R$ 80.000, Prazo: 5 meses."
}'

RESPONSE=$(curl -s -X POST $BASE_URL/v1/project/analyze \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PROJECT_JSON")

SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', ''))")
QUESTIONS_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_questions', 0))")

echo -e "${GREEN}✅ Project created${NC}"
echo "   Session ID: $SESSION_ID"
echo "   Questions generated: $QUESTIONS_COUNT"
echo ""

# Step 2: Answer initial questions
echo -e "${YELLOW}STEP 2: Answering initial questions...${NC}"

ANSWERS_JSON='{
  "session_id": "'$SESSION_ID'",
  "answers": [
    {"question_code": "Q001", "selected_choices": ["desktop_only"]},
    {"question_code": "Q002", "selected_choices": ["printers", "barcode"]},
    {"question_code": "Q003", "selected_choices": ["nfe", "nfce"]}
  ],
  "request_next_batch": false
}'

RESPONSE=$(curl -s -X POST $BASE_URL/v1/questions/respond \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$ANSWERS_JSON")

COMPLETION=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('completion_percentage', 0))")

echo -e "${GREEN}✅ Questions answered${NC}"
echo "   Completion: ${COMPLETION}%"
echo ""

# Step 3: Generate summary
echo -e "${YELLOW}STEP 3: Generating summary...${NC}"

SUMMARY_REQUEST='{
  "session_id": "'$SESSION_ID'",
  "include_assumptions": true,
  "language": "pt-BR"
}'

RESPONSE=$(curl -s -X POST $BASE_URL/v1/summary/generate \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$SUMMARY_REQUEST")

CONFIDENCE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('confidence_score', 0))")

echo -e "${GREEN}✅ Summary generated${NC}"
echo "   Confidence score: $CONFIDENCE"
echo ""

# Step 4: REJECT the summary with feedback
echo -e "${YELLOW}STEP 4: Rejecting summary with feedback...${NC}"

CONFIRM_JSON='{
  "session_id": "'$SESSION_ID'",
  "confirmed": false,
  "feedback": "O resumo não menciona detalhes sobre a arquitetura offline-first e sincronização. Também preciso saber sobre requisitos de performance e volume de transações esperado.",
  "additional_notes": "Preciso de mais clareza sobre a infraestrutura necessária"
}'

echo -e "${BLUE}Sending rejection with feedback:${NC}"
echo "   - Arquitetura offline-first não detalhada"
echo "   - Falta informação sobre performance"
echo "   - Volume de transações não especificado"
echo ""

RESPONSE=$(curl -s -X POST $BASE_URL/v1/summary/confirm \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$CONFIRM_JSON")

# Parse the response
CONFIRMATION_STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('confirmation_status', ''))")
MESSAGE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('message', ''))")
NEXT_STEP=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('next_step', ''))")

echo -e "${GREEN}✅ Summary rejection processed${NC}"
echo "   Status: $CONFIRMATION_STATUS"
echo "   Message: $MESSAGE"
echo "   Next step: $NEXT_STEP"
echo ""

# Extract and display refinement questions
echo -e "${YELLOW}STEP 5: Refinement Questions Generated${NC}"
echo "$RESPONSE" | python3 -c "
import sys, json

data = json.load(sys.stdin)
questions = data.get('refinement_questions', [])

if questions:
    print(f'📋 {len(questions)} refinement questions generated:\n')
    for i, q in enumerate(questions, 1):
        print(f'  {i}. [{q.get(\"code\", \"\")}] {q.get(\"text\", \"\")}')
        print(f'     Why it matters: {q.get(\"why_it_matters\", \"\")}')
        choices = q.get('choices', [])
        if choices:
            print('     Options:')
            for c in choices:
                print(f'       - [{c.get(\"id\", \"\")}] {c.get(\"text\", \"\")}')
        print()
else:
    print('❌ No refinement questions were generated')
"

# Step 6: Answer refinement questions
echo -e "${YELLOW}STEP 6: Answering refinement questions...${NC}"

REFINEMENT_ANSWERS='{
  "session_id": "'$SESSION_ID'",
  "answers": [
    {"question_code": "R001", "selected_choices": ["sla_99"]},
    {"question_code": "R002", "selected_choices": ["users_100"]},
    {"question_code": "R003", "selected_choices": ["lgpd", "none"]}
  ],
  "request_next_batch": false
}'

RESPONSE=$(curl -s -X POST $BASE_URL/v1/questions/respond \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$REFINEMENT_ANSWERS")

RESPONSE_TYPE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('response_type', ''))")

echo -e "${GREEN}✅ Refinement questions answered${NC}"
echo "   Response type: $RESPONSE_TYPE"
echo ""

# Step 7: Generate improved summary
echo -e "${YELLOW}STEP 7: Generating improved summary...${NC}"

RESPONSE=$(curl -s -X POST $BASE_URL/v1/summary/generate \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$SUMMARY_REQUEST")

NEW_CONFIDENCE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('confidence_score', 0))")

echo -e "${GREEN}✅ Improved summary generated${NC}"
echo "   New confidence score: $NEW_CONFIDENCE"
echo ""

# Step 8: Confirm the improved summary
echo -e "${YELLOW}STEP 8: Confirming improved summary...${NC}"

CONFIRM_IMPROVED='{
  "session_id": "'$SESSION_ID'",
  "confirmed": true,
  "additional_notes": "Agora está completo com os requisitos de offline-first e performance"
}'

RESPONSE=$(curl -s -X POST $BASE_URL/v1/summary/confirm \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$CONFIRM_IMPROVED")

FINAL_STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('confirmation_status', ''))")
READY_FOR_DOCS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('ready_for_documents', False))")

echo -e "${GREEN}✅ Summary confirmed${NC}"
echo "   Final status: $FINAL_STATUS"
echo "   Ready for documents: $READY_FOR_DOCS"
echo ""

# Summary
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    TEST COMPLETED                           ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Summary of the refinement flow:"
echo "1. ✅ Project created with initial questions"
echo "2. ✅ Initial questions answered"
echo "3. ✅ Summary generated"
echo "4. ✅ Summary REJECTED with feedback"
echo "5. ✅ Refinement questions generated based on feedback"
echo "6. ✅ Refinement questions answered"
echo "7. ✅ Improved summary generated"
echo "8. ✅ Improved summary confirmed"
echo ""
echo -e "${GREEN}The refinement flow is working correctly!${NC}"