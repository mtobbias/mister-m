#!/bin/bash

echo "Starting Ollama server..."
/bin/ollama serve &
sleep 5
echo "==================================================="
echo "======            FALCON-OLLAMA            ========"
echo "==================================================="
echo "======          AGUARDE O DOWNLOAD         ========"
echo "==================================================="
/bin/ollama pull mxbai-embed-large:latest &
/bin/ollama pull gemma3:1b &

wait
tail -f /dev/null