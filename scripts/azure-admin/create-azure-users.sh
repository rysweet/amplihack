#!/bin/bash
# Create missing Azure AD accounts

DOMAIN="DefenderATEVET12.onmicrosoft.com"
# Generate a temporary password (users will need to change on first login)
TEMP_PASSWORD="TempPass123!@#"

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
echo "All accounts created with temporary password: $TEMP_PASSWORD"
echo "Users will be required to change password on first login."
