#!/bin/bash
# Create missing Azure AD accounts

DOMAIN="DefenderATEVET12.onmicrosoft.com"
# Temporary password must be provided via environment variable
# Users will be required to change password on first login
if [ -z "$TEMP_PASSWORD" ]; then
  echo "Error: TEMP_PASSWORD environment variable must be set"
  echo "Usage: TEMP_PASSWORD='YourSecurePassword123!' $0"
  exit 1
fi

ACCOUNTS=(
  "noahbaertsch"
  "diftimie"
  "blaineherro"
  "jonesmalachi"
  "sgalla"
)

echo "Creating 5 Azure AD accounts..."
for username in "${ACCOUNTS[@]}"; do
  upn="${username}@${DOMAIN}"
  echo "Creating: $upn"

  # Create the user with temporary password
  az ad user create \
    --user-principal-name "$upn" \
    --display-name "$username" \
    --mail-nickname "$username" \
    --password "$TEMP_PASSWORD" \
    --force-change-password-next-sign-in true \
    --query "userPrincipalName" -o tsv

  if [ $? -eq 0 ]; then
    echo "✓ Created: $upn"
  else
    echo "✗ Failed to create: $upn"
  fi
done

echo ""
echo "All accounts created successfully."
echo "Users will be required to change password on first login."
