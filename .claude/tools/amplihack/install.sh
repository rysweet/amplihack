#!/bin/bash
# if the AMPLIHACK_INSTALL_LOCATION variable is not set, default to https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding
AMPLIHACK_INSTALL_LOCATION=${AMPLIHACK_INSTALL_LOCATION:-https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding}

# clone the repository to a tmp local directory
# make sure the dir does not exist first - exit if it does
if [ -d "./tmpamplihack" ]; then
  echo "Error: ./tmpamplihack directory already exists. Please remove it and try again."
  exit 1
fi

git clone $AMPLIHACK_INSTALL_LOCATION ./tmpamplihack

# copy the contents of the tmp local directory to the ~/.claude directory
cp -r ./tmpamplihack/.claude ~/

# remove the tmp local directory
rm -rf ./tmpamplihack
