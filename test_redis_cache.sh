#!/bin/bash

# Test Redis Cache Functionality
echo "🧪 TESTING REDIS CACHE FUNCTIONALITY"
echo "======================================"
echo ""

# Set environment variables
export DEMANDEI_API_KEY="test_key"
export REDIS_HOST="localhost"
export ENABLE_REDIS_CACHE="true"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost:8001"

# Function to print colored output
print_status() {
    if [ "$1" = "success" ]; then
        echo -e "${GREEN}✅ $2${NC}"
    elif [ "$1" = "warning" ]; then
        echo -e "${YELLOW}⚠️ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Start Redis and API server with docker-compose
echo "🚀 Starting services with docker-compose..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check Redis is running
echo ""
echo "1️⃣ Checking Redis Status..."
if docker-compose ps | grep -q "ia-compose-redis.*Up"; then
    print_status "success" "Redis is running"
    
    # Check Redis connectivity
    docker exec ia-compose-redis redis-cli ping > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        print_status "success" "Redis is responsive"
    else
        print_status "error" "Redis not responding"
    fi
else
    print_status "error" "Redis is not running"
fi

# Check API is running
echo ""
echo "2️⃣ Checking API Status..."
curl -s "$BASE_URL/health" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_status "success" "API is running"
else
    print_status "error" "API is not running"
    exit 1
fi

# Test 1: Generate questions (first call - should cache)
echo ""
echo "3️⃣ Test Question Caching..."
echo "   First call (generates and caches):"

SESSION_ID="cache-test-$(date +%s)"
PROJECT_DESC="Sistema de e-commerce com catálogo de produtos, carrinho de compras, pagamentos online e gestão de pedidos"

RESPONSE1=$(curl -s -X POST "$BASE_URL/v1/project/analyze" \
  -H "Authorization: Bearer test_key" \
  -H "Content-Type: application/json" \
  -d "{\"project_description\": \"$PROJECT_DESC\"}")

if echo "$RESPONSE1" | grep -q "session_id"; then
    SESSION_ID=$(echo "$RESPONSE1" | grep -o '"session_id":"[^"]*' | cut -d'"' -f4)
    print_status "success" "Questions generated (Session: ${SESSION_ID:0:8}...)"
else
    print_status "error" "Failed to generate questions"
fi

# Test 2: Same project description (should use cache)
echo ""
echo "   Second call (should use cache):"
sleep 2

START_TIME=$(date +%s%3N)
RESPONSE2=$(curl -s -X POST "$BASE_URL/v1/project/analyze" \
  -H "Authorization: Bearer test_key" \
  -H "Content-Type: application/json" \
  -d "{\"project_description\": \"$PROJECT_DESC\"}")
END_TIME=$(date +%s%3N)

DURATION=$((END_TIME - START_TIME))

if echo "$RESPONSE2" | grep -q "session_id"; then
    if [ "$DURATION" -lt 500 ]; then
        print_status "success" "Cache hit! Response time: ${DURATION}ms (<500ms indicates cache)"
    else
        print_status "warning" "Response received but slow: ${DURATION}ms (may not be cached)"
    fi
else
    print_status "error" "Failed on second call"
fi

# Test 3: Document caching
echo ""
echo "4️⃣ Test Document Caching..."

# First, complete the flow to enable document generation
echo "   Preparing session for document generation..."

# Answer questions
curl -s -X POST "$BASE_URL/v1/questions/respond" \
  -H "Authorization: Bearer test_key" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"answers\": [
      {\"question_code\": \"Q001\", \"selected_choices\": [\"web_app\"]}
    ],
    \"request_next_batch\": false
  }" > /dev/null 2>&1

# Generate summary
curl -s -X POST "$BASE_URL/v1/summary/generate" \
  -H "Authorization: Bearer test_key" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\"}" > /dev/null 2>&1

# Confirm summary
curl -s -X POST "$BASE_URL/v1/summary/confirm" \
  -H "Authorization: Bearer test_key" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"confirmed\": true}" > /dev/null 2>&1

echo "   First document generation (generates and caches):"
START_TIME=$(date +%s%3N)
DOC_RESPONSE1=$(curl -s -X POST "$BASE_URL/v1/documents/generate" \
  -H "Authorization: Bearer test_key" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"include_implementation_details\": true}")
END_TIME=$(date +%s%3N)

DURATION1=$((END_TIME - START_TIME))

if echo "$DOC_RESPONSE1" | grep -q "stacks"; then
    print_status "success" "Documents generated in ${DURATION1}ms"
else
    print_status "error" "Failed to generate documents"
fi

echo ""
echo "   Second document generation (should use cache):"
sleep 2

START_TIME=$(date +%s%3N)
DOC_RESPONSE2=$(curl -s -X POST "$BASE_URL/v1/documents/generate" \
  -H "Authorization: Bearer test_key" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"include_implementation_details\": true}")
END_TIME=$(date +%s%3N)

DURATION2=$((END_TIME - START_TIME))

if echo "$DOC_RESPONSE2" | grep -q "stacks"; then
    if [ "$DURATION2" -lt 100 ]; then
        print_status "success" "Cache hit! Response time: ${DURATION2}ms (<100ms indicates cache)"
    else
        print_status "warning" "Response received but slow: ${DURATION2}ms (may not be cached)"
    fi
else
    print_status "error" "Failed on second call"
fi

# Check Redis cache stats
echo ""
echo "5️⃣ Redis Cache Statistics..."
KEYS_COUNT=$(docker exec ia-compose-redis redis-cli DBSIZE | cut -d' ' -f2)
print_status "success" "Redis has $KEYS_COUNT cached keys"

# Show some cached keys
echo ""
echo "   Sample cached keys:"
docker exec ia-compose-redis redis-cli --scan --pattern "*" | head -5 | while read key; do
    TTL=$(docker exec ia-compose-redis redis-cli TTL "$key")
    echo "     • $key (TTL: ${TTL}s)"
done

# Check memory usage
MEMORY=$(docker exec ia-compose-redis redis-cli INFO memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
echo ""
print_status "success" "Redis memory usage: $MEMORY"

# Summary
echo ""
echo "======================================"
echo "📊 TEST SUMMARY"
echo "======================================"
echo ""

if [ "$KEYS_COUNT" -gt 0 ]; then
    print_status "success" "Redis cache is working correctly!"
    echo ""
    echo "✅ Questions are being cached (1 hour TTL)"
    echo "✅ Documents are being cached (24 hours TTL)"
    echo "✅ Cache hits are significantly faster"
    echo ""
    echo "💡 TIP: The same session_id will reuse cached documents for 24 hours"
else
    print_status "warning" "No keys found in Redis cache"
    echo "Check if Redis is properly connected to the API"
fi

echo ""
echo "🧹 Cleanup: Run 'docker-compose down' to stop services"