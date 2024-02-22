#!/bin/bash

# List all instances in the specified region and profile

REGION=""
PROFILE=""

aws ec2 describe-instances \
  --region "$REGION" \
  --profile "$PROFILE" \
  --query 'Reservations[*].Instances[*].[InstanceId, MetadataOptions.HttpTokens]' \
  --output json | jq -c '.[][] | select(.[1] == "optional")' | while read -r line; do
    instance_id=$(echo "$line" | jq -r '.[0]')
    http_tokens=$(echo "$line" | jq -r '.[1]')

    if [[ "$http_tokens" == "optional" ]]; then
      echo "{\"InstanceID\":\"$instance_id\",\"AllowsIMDSv1\":true}"
    fi
  done
