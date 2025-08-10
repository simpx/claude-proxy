#!/bin/bash
# Comprehensive curl tests for Claude API Proxy

BASE_URL="http://localhost:8085"
API_KEY="test-key"

echo "🚀 Claude API Proxy End-to-End Tests"
echo "====================================="

# Test 1: Health Check
echo -e "\n1️⃣ Health Check"
echo "curl -s $BASE_URL/health | jq"
curl -s "$BASE_URL/health" | jq

# Test 2: Root Endpoint
echo -e "\n2️⃣ Root Endpoint Info"
echo "curl -s $BASE_URL/ | jq"
curl -s "$BASE_URL/" | jq

# Test 3: Connection Test
echo -e "\n3️⃣ Connection Test"
echo "curl -s $BASE_URL/test-connection | jq"
curl -s "$BASE_URL/test-connection" | jq

# Test 4: Token Counting
echo -e "\n4️⃣ Token Counting"
echo "Testing token count for 'Hello, how are you?'"
curl -s -X POST "$BASE_URL/v1/messages/count_tokens" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [{"role": "user", "content": "Hello, how are you?"}]
  }' | jq

# Test 5: Simple Haiku Request
echo -e "\n5️⃣ Claude Haiku (Small Model)"
echo "Simple greeting request to claude-3-haiku"
curl -s -X POST "$BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "max_tokens": 50,
    "messages": [{"role": "user", "content": "Say hello briefly"}]
  }' | jq '.model, .content[0].text, .usage'

# Test 6: Sonnet Request with System Prompt
echo -e "\n6️⃣ Claude Sonnet (Big Model) with System"
echo "Request with system prompt"
curl -s -X POST "$BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 100,
    "system": "You are a helpful coding assistant. Always respond with working code.",
    "messages": [{"role": "user", "content": "Write a Python function to calculate factorial"}]
  }' | jq '.model, .content[0].text[:100], .usage'

# Test 7: Multi-turn Conversation
echo -e "\n7️⃣ Multi-turn Conversation"
echo "Testing conversation memory"
curl -s -X POST "$BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "max_tokens": 50,
    "messages": [
      {"role": "user", "content": "My favorite color is blue"},
      {"role": "assistant", "content": "I understand that blue is your favorite color."},
      {"role": "user", "content": "What is my favorite color?"}
    ]
  }' | jq '.content[0].text'

# Test 8: Model Mapping Test
echo -e "\n8️⃣ Model Mapping Tests"
echo "Testing Opus -> Big Model mapping"
curl -s -X POST "$BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "claude-3-opus-20240229",
    "max_tokens": 30,
    "messages": [{"role": "user", "content": "Just say your model name"}]
  }' | jq '.model'

# Test 9: Error Handling - Invalid Model
echo -e "\n9️⃣ Error Handling - Invalid Model"
echo "Testing with invalid model name"
curl -s -X POST "$BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "totally-invalid-model",
    "max_tokens": 30,
    "messages": [{"role": "user", "content": "test"}]
  }' | jq -c

# Test 10: Error Handling - Missing Required Fields
echo -e "\n🔟 Error Handling - Missing Messages"
echo "Testing validation with missing messages"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "max_tokens": 30
  }')
echo "HTTP Status Code: $HTTP_CODE (should be 422)"

# Test 11: Load Test - Multiple Concurrent Requests
echo -e "\n1️⃣1️⃣ Basic Load Test"
echo "Running 5 concurrent simple requests..."
for i in {1..5}; do
  curl -s -X POST "$BASE_URL/v1/messages" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d '{
      "model": "claude-3-haiku-20240307",
      "max_tokens": 20,
      "messages": [{"role": "user", "content": "Count: '$i'"}]
    }' | jq -r '.content[0].text' &
done
wait
echo "✅ All 5 requests completed"

echo -e "\n🎉 All tests completed!"
echo "Check proxy server logs for detailed request processing info"