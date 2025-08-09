#!/bin/bash

# Test the dashscope API endpoint
echo "Testing dashscope API endpoint..."

curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-bdd3ea1a9cee489b890e11c60fe929f4" \
  -d '{
    "model": "qwen-plus",
    "messages": [
      {
        "role": "user", 
        "content": "Hello"
      }
    ],
    "max_tokens": 100
  }' \
  -v

echo -e "\n\nTesting alternative endpoint..."

# Test alternative endpoint without compatible-mode
curl -X POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-bdd3ea1a9cee489b890e11c60fe929f4" \
  -d '{
    "model": "qwen-plus",
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "Hello"
        }
      ]
    },
    "parameters": {
      "max_tokens": 100
    }
  }' \
  -v
