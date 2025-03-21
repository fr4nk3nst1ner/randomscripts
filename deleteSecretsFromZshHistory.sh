# add this to your ~/.zshrc file 
# ensure you have trufflehog installed and in your path 

remove_secrets_from_history() {
  local history_file="$HOME/.zsh_history"
  local backup_file="$HOME/.zsh_history.bak.$(date +%Y%m%d%H%M%S)"
  local temp_file=$(mktemp)
  local tmp_cleaned_file=$(mktemp)

  echo "🔍 Running TruffleHog on $history_file..."
  
  # Run TruffleHog in JSON mode and save output
  trufflehog filesystem "$history_file" --json > "$temp_file" 2>/dev/null

  if [[ ! -s "$temp_file" ]]; then
    echo "✅ No secrets found in history."
    rm -f "$temp_file"
    return 0
  fi

  echo "⚠️  Secrets detected! Extracting them for removal..."

  # Extract actual secret-containing entries from ~/.zsh_history
  # Handle multiline entries better by using NUL as delimiter
  local secret_entries=()
  while IFS= read -r -d $'\0' entry; do
    secret_entries+=("$entry")
  done < <(jq -r 'select(.Raw != null) | .Raw' "$temp_file" | tr '\n' '\0')
  
  rm -f "$temp_file"  # Cleanup temp file

  if [[ ${#secret_entries[@]} -eq 0 ]]; then
    echo "⚠️  No specific entries found for removal. Exiting."
    return 1
  fi

  echo "📋 Found ${#secret_entries[@]} suspicious history entries."
  
  # Show preview of what will be removed (first 50 chars of each entry)
  echo "🔍 Preview of entries to be removed:"
  for entry in "${secret_entries[@]}"; do
    preview="${entry:0:50}"
    echo "   - ${preview}${preview:50:1000}..."
  done
  
  # Ask for confirmation using zsh-compatible syntax
  echo -n "Continue with removal? (y/n) "
  read -k 1 REPLY
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "🛑 Operation cancelled."
    return 1
  fi

  # Backup history before modification with timestamp
  cp "$history_file" "$backup_file"
  echo "📦 Backup of history saved to $backup_file"

  # Use macOS-friendly approach to remove entries
  touch "$tmp_cleaned_file"
  
  # Read history file line by line and exclude matched entries
  while IFS= read -r line; do
    matched=false
    for secret in "${secret_entries[@]}"; do
      if [[ "$line" == *"$secret"* ]]; then
        matched=true
        break
      fi
    done
    
    if ! $matched; then
      echo "$line" >> "$tmp_cleaned_file"
    fi
  done < "$history_file"

  # Ensure the cleaned file is not empty before replacing the original history
  if [[ -s "$tmp_cleaned_file" ]]; then
    # Set permissions to match original file
    chmod "$(stat -f %p "$history_file" | cut -c 3-)" "$tmp_cleaned_file" 
    mv "$tmp_cleaned_file" "$history_file"
    echo "✅ Removed ${#secret_entries[@]} entries containing secrets from $history_file."
  else
    echo "❌ Error: Cleanup resulted in empty history! Restoring from backup."
    cp "$backup_file" "$history_file"
    rm -f "$tmp_cleaned_file"
    return 1
  fi

  # Clear in-memory Zsh history safely for macOS
  fc -p "$history_file"  # Switch to our cleaned history file
  fc -P              # Save current history
  
  # Ask if user wants to delete the backup file
  echo -n "Delete backup file? (y/n) "
  read -k 1 DELETE_REPLY
  echo
  if [[ $DELETE_REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Deleting backup file $backup_file"
    rm "$backup_file"
  else
    echo "👉 Keeping backup file: $backup_file"
  fi
  
  echo "🧹 Shell history updated. For complete effect, you may need to restart your terminal."
}
