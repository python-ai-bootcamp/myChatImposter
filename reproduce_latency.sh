#!/bin/bash

# Check for API Key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable is not set."
    echo "Please set it: export OPENAI_API_KEY='sk-...'"
    exit 1
fi

MODEL="gpt-5-nano"

echo "Testing latency for model: $MODEL"
echo "Endpoint: https://api.openai.com/v1/chat/completions"
echo "Please wait..."

# Define the JSON payload
# We are reproducing the exact state seen in logs:
# 1. System Prompt
# 2. History Message (HumanMessage)
# 3. New User Message (formatted as "Sender: Content")
# Note: In your specific log case, the history and the new message were identical ("Tal Shachar: הי").

JSON_PAYLOAD=$(cat <<EOF
{
  "model": "$MODEL",
  "temperature": 1,
  "reasoning_effort": "minimal",
  "messages": [
    {
      "role": "system",
      "content": "You are Yahav, a curly mischievous boy, sun of his father tal and his mother orly. your brother is ron and you got a love/hate relationship with him. you are mimicking an actual interaction as if you're a real person on a chat app. you are worried that mother is being too late today coming back from work"
    },
    {
      "role": "user",
      "content": "Tal Shachar: הי"
    },
    {
      "role": "user",
      "content": "Tal Shachar: הי"
    }
  ]
}
EOF
)

# Run curl with time to measure duration
# -w formatted output to see timing details from curl itself
curl -s -w "\n\nDNS Lookup: %{time_namelookup}s\nConnect: %{time_connect}s\nStart Transfer: %{time_starttransfer}s\nTotal Time: %{time_total}s\n" \
     https://api.openai.com/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $OPENAI_API_KEY" \
     -d "$JSON_PAYLOAD"
