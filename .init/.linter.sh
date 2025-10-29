#!/bin/bash
cd /home/kavia/workspace/code-generation/azure-echo-chatbot-tester-26234-26243/echo_chatbot_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

