#!/bin/bash

# Set AWS CLI profile and region
AWS_PROFILE="growth"
AWS_REGION="us-west-2"
NAMESPACE="aws:elasticbeanstalk:application:environment"

echo "Application,Environment,OptionName,Value"  # CSV Header

# Get list of all Elastic Beanstalk applications
applications=$(aws elasticbeanstalk describe-applications --region "$AWS_REGION" --profile "$AWS_PROFILE" --query 'Applications[].ApplicationName' --output text)

# Iterate over each application to get its environments
for app in $applications; do
    # Get environment names for the application
    environments=$(aws elasticbeanstalk describe-environments --application-name "$app" --region "$AWS_REGION" --profile "$AWS_PROFILE" --query 'Environments[].EnvironmentName' --output text)

    for env in $environments; do
        # Get the configuration settings in JSON format
        config=$(aws elasticbeanstalk describe-configuration-settings --application-name "$app" --environment-name "$env" --region "$AWS_REGION" --profile "$AWS_PROFILE" --query "ConfigurationSettings[0].OptionSettings[?Namespace=='$NAMESPACE']" --output json)

        # Use jq to parse the configuration settings and output CSV lines
        echo "$config" | jq -r --arg app "$app" --arg env "$env" ".[] | [\$app, \$env, .OptionName, .Value] | @csv"
    done
done
