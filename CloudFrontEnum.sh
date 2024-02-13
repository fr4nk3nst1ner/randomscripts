#!/bin/bash

# This script enumerates CloudFront and finds all URLs and associated PathPatterns from the config
# Useful when trying to enumerate an application (e.g., Beanstalk) that leverages CloudFront

# Function to retrieve full URL for a given path pattern and target origin
get_full_url() {
  local path_pattern=$1
  local target_origin_id=$2
  local distribution_id=$3
  s3_origin_domain=$(aws cloudfront get-distribution-config --id "${distribution_id}" --output json | jq -r --arg TOI "$target_origin_id" '.DistributionConfig.Origins.Items[] | select(.Id == $TOI) | .DomainName')
  full_url="${s3_origin_domain}${path_pattern}"
  echo "$full_url"
}

# Set the AWS profile and region
export AWS_PROFILE=profilename
export AWS_DEFAULT_REGION=regionname

# Get the details of all CloudFront distributions in JSON format
distribution_details_json=$(aws cloudfront list-distributions --query 'DistributionList.Items[].[Id, DomainName]' --output json)

# Initialize the JSON array to store distribution details
echo "["

# Iterate through each distribution to get its details
while IFS= read -r row; do
  distribution_id=$(echo "${row}" | jq -r '.[0]')
  domain_name=$(echo "${row}" | jq -r '.[1]')
  
  # Initialize the JSON object for the current distribution
  echo "  {"
  echo "    \"distributionId\": \"$distribution_id\","
  echo "    \"domainName\": \"$domain_name\","
  echo "    \"urlsWithPathPatterns\": ["

  # Get CloudFront distribution configuration in JSON format
  distribution_config_json=$(aws cloudfront get-distribution-config --id "${distribution_id}" --output json)

  # Check if cache behaviors exist before extracting URLs and their corresponding PathPatterns
  if [[ $(echo "${distribution_config_json}" | jq -r '.DistributionConfig.CacheBehaviors.Quantity') != 0 ]]; then
    urls_with_pathpatterns=$(echo "${distribution_config_json}" | jq -r '.DistributionConfig.CacheBehaviors.Items[] | "\(.PathPattern) => \(.TargetOriginId)"')

    while IFS= read -r line; do
      path_pattern=$(echo "$line" | awk -F "=>" '{print $1}' | xargs)
      target_origin_id=$(echo "$line" | awk -F "=>" '{print $2}' | xargs)
      full_url=$(get_full_url "$path_pattern" "$target_origin_id" "$distribution_id")
      
      # Add the URL with PathPattern to the JSON array
      echo "      {"
      echo "        \"pathPattern\": \"$path_pattern\","
      echo "        \"fullURL\": \"$full_url\""
      echo "      },"
    done <<< "$urls_with_pathpatterns"
  else
    echo "No cache behaviors found for this distribution."
  fi
  
  # Remove trailing comma from the last item in the JSON array, if it exists
  echo "    ]"
  echo "  },"

done <<< "$(echo "${distribution_details_json}" | jq -c '.[]')"

# Remove trailing comma from the last distribution object in the JSON array, if it exists
echo "]"
