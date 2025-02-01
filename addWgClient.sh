#!/bin/bash

# Define paths
WG_CONFIG="/etc/wireguard/wg0.conf"
BACKUP_DIR="~/wireguard"
BACKUP_CONFIG="$BACKUP_DIR/wg_server.conf"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Step 1: Backup existing WireGuard config
cp "$WG_CONFIG" "$BACKUP_CONFIG"

# Step 2: Get user input for client details
read -p "Enter the client name (for comment): " CLIENT_NAME
read -p "Enter the client's public key: " CLIENT_PUBLIC_KEY
read -p "Enter the client's allowed IP (e.g., 10.0.0.X/32): " CLIENT_ALLOWED_IP

# Validate Allowed IP format
if [[ ! $CLIENT_ALLOWED_IP =~ ^10\.0\.0\.[0-9]+/32$ ]]; then
    echo "Error: Allowed IP must be in the format 10.0.0.X/32"
    exit 1
fi

# Step 5: Add the new client entry to the backup configuration
echo -e "\n# $CLIENT_NAME\n[Peer]\nPublicKey = $CLIENT_PUBLIC_KEY\nAllowedIPs = $CLIENT_ALLOWED_IP" >> "$BACKUP_CONFIG"

# Step 6: Stop WireGuard interface
echo "Stopping WireGuard..."
sudo wg-quick down wg0

# Step 7: Copy the updated config back to WireGuard
cp "$BACKUP_CONFIG" "$WG_CONFIG"

# Step 8: Restart WireGuard interface
echo "Starting WireGuard..."
sudo wg-quick up wg0

echo "Client $CLIENT_NAME successfully added!"
