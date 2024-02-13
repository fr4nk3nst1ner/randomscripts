#!/bin/bash

# This script enumerates CloudFront and finds all URLs and associated PathPatterns from the config
# Useful when trying to enumerate an application (e.g., Beanstalk) that leverages CloudFront

# Set the AWS profile and region
export AWS_PROFILE=profilename
export AWS_DEFAULT_REGION=regionname

# Get the details of all CloudFront distributions in JSON format
distribution_details_json=$(aws cloudfront list-distributions --query 'DistributionList.Items[].[Id, DomainName]' --output json)

# Iterate through each distribution to get its details
for row in $(echo "${distribution_details_json}" | jq -r '.[] | @base64'); do
  _jq() {
    echo ${row} | base64 --decode | jq -r ${1}
  }

  distribution_id=$(_jq '.[0]')
  domain_name=$(_jq '.[1]')

  echo "Retrieving details for distribution: ${distribution_id} - ${domain_name}"

  # Get CloudFront distribution configuration in JSON format
  distribution_config_json=$(aws cloudfront get-distribution-config --id "${distribution_id}" --output json)

  # Check if cache behaviors exist before extracting URLs and their corresponding PathPatterns
  if [[ $(echo "${distribution_config_json}" | jq -r '.DistributionConfig.CacheBehaviors.Quantity') != 0 ]]; then
    # Extract URLs and their corresponding PathPatterns using jq
    urls_with_pathpatterns=$(echo "${distribution_config_json}" | jq -r '.DistributionConfig.CacheBehaviors.Items[] | "\(.PathPattern) => https://\(.TargetOriginId)\(.PathPattern)"')

    # Display the extracted URLs and PathPatterns
    echo "URLs with PathPatterns:"
    echo "${urls_with_pathpatterns}"
  else
    echo "No cache behaviors found for this distribution."
  fi

  echo "---------------------------------------"
done
