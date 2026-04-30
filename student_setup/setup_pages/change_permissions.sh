#!/bin/bash
# set_course_perms.sh
# Script to update permissions for course folders inside a list of user home directories

# Exit on error
set -e

# Base directory
BASE_DIR="/home"

# List of users (edit this list as needed)
USER_LIST=("demostudent2")

echo "🔧 Updating permissions for course folders for selected users..."

for username in "${USER_LIST[@]}"; do
  userdir="$BASE_DIR/$username"
  if [ -d "$userdir" ]; then
    for coursedir in "$userdir"/ps1; do
      for assdir in "$coursedir"/*; do
        if [ -d "$assdir" ]; then
          echo "Setting permissions for $assdir"
          chmod -R 000 "$assdir"
        fi
      done
    done
  else
    echo "⚠️ Skipping $username (no directory found)"
  fi
done

echo "✅ Permissions updated successfully."
