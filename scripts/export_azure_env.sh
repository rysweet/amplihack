#!/bin/bash
# Export Azure environment variables
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    if [[ ! "$key" =~ ^# ]] && [[ -n "$key" ]]; then
        # Remove quotes from value if present
        value="${value%\"}"
        value="${value#\"}"
        export "$key=$value"
        echo "Exported $key"
    fi
done < .azure.env
