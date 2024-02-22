#!/bin/bash

# Set the AWS CLI profile and region
AWS_PROFILE="growth"
AWS_REGION="us-west-2"

# Fetch all instance IDs in the specified region
instance_ids=$(aws ec2 describe-instances \
                --query 'Reservations[*].Instances[*].InstanceId' \
                --region "$AWS_REGION" \
                --profile "$AWS_PROFILE" \
                --output text)

# Loop through each instance ID
for instance_id in $instance_ids; do
    # Fetch MetadataOptions for the current instance
    metadata_options=$(aws ec2 describe-instances \
                        --instance-ids "$instance_id" \
                        --query "Reservations[0].Instances[0].MetadataOptions" \
                        --region "$AWS_REGION" \
                        --profile "$AWS_PROFILE" \
                        --output text)

    # Check if HttpTokens value is 'optional', indicating IMDSv1 is enabled
    http_tokens=$(echo "$metadata_options" | awk '{print $1}') # Assuming HttpTokens is the first item in MetadataOptions
    if [ "$http_tokens" == "optional" ]; then
        echo "Instance ID with IMDSv1 enabled: $instance_id"
    fi
done
