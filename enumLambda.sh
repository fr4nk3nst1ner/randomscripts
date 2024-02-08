#!/bin/bash

# Specify the AWS region and profile to use 
region=''
profile=''

echo "Fetching Lambda functions in region $region using the '$profile' profile..."

# List all Lambda functions using the specified profile
function_names=$(aws lambda list-functions --region "$region" --profile "$profile" --query 'Functions[].FunctionName' --output text)

# Loop through the function names
for name in $function_names; do
  echo "Function: $name"

  # Check for REST APIs associated with the Lambda function
  rest_apis=$(aws apigateway get-rest-apis --region "$region" --profile "$profile" --query 'items[?contains(name, `'"$name"'`)].{id:id, name:name}' --output text)
  if [ "$rest_apis" != "None" ]; then
    echo "  - Associated REST API(s):"
    IFS=$'\n'
    for api in $rest_apis; do
      read -ra ADDR <<< "$api"
      api_id=${ADDR[0]}
      stage_names=$(aws apigateway get-stages --rest-api-id "$api_id" --region "$region" --profile "$profile" --query 'item[].stageName' --output text)
      for stage_name in $stage_names; do
        echo "    - Exposed URL: https://${api_id}.execute-api.$region.amazonaws.com/$stage_name"
      done
    done
    unset IFS
  else
    echo "  - No associated REST API(s)."
  fi

  # Check for HTTP APIs associated with the Lambda function
  http_apis=$(aws apigatewayv2 get-apis --region "$region" --profile "$profile" --query 'Items[?contains(Name, `'"$name"'`)].{ApiId:ApiId, Name:Name}' --output text)
  if [ "$http_apis" != "None" ]; then
    echo "  - Associated HTTP API(s):"
    IFS=$'\n'
    for api in $http_apis; do
      read -ra ADDR <<< "$api"
      api_id=${ADDR[0]}
      stage_names=$(aws apigatewayv2 get-stages --api-id "$api_id" --region "$region" --profile "$profile" --query 'Items[].StageName' --output text)
      for stage_name in $stage_names; do
        echo "    - Exposed URL: https://${api_id}.execute-api.$region.amazonaws.com/$stage_name"
      done
    done
    unset IFS
  else
    echo "  - No associated HTTP API(s)."
  fi

  # Get the Lambda function's resource policy
  policy=$(aws lambda get-policy --function-name "$name" --region "$region" --profile "$profile" --query 'Policy' --output text 2>/dev/null)
  if [[ "$policy" != "" ]]; then
    # Check if the policy allows public access
    if echo "$policy" | jq 'select(.Statement[] | select(.Effect == "Allow" and .Principal == "*" and .Action == "lambda:InvokeFunction"))' &>/dev/null; then
      echo "  - Public Invoke Policy: Yes"
      echo "  - AWS CLI command to invoke the Lambda function:"
      echo "    aws lambda invoke --function-name $name --profile $profile --region $region outputfile.txt"
    else
      echo "  - Public Invoke Policy: No"
    fi
  else
    echo "  - No resource policy found."
  fi

  # Fetch and display the function's execution role
  execution_role=$(aws lambda get-function-configuration --function-name "$name" --region "$region" --profile "$profile" --query 'Role' --output text)
  echo "  - Execution Role: $execution_role"

  # List the event source mappings (triggers)
  echo "  - Event Source Mappings (Triggers):"
  mappings=$(aws lambda list-event-source-mappings --function-name "$name" --region "$region" --profile "$profile" --query 'EventSourceMappings[].{UUID:UUID, EventSourceArn:EventSourceArn}' --output text)
  if [ -z "$mappings" ]; then
    echo "    None"
  else
    echo "$mappings" | while read -r line; do
      uuid=$(echo $line | awk '{print $1}')
      source_arn=$(echo $line | awk '{print $2}')
      echo "    UUID: $uuid, Source ARN: $source_arn"
    done
  fi

  # Check for Lambda URL configurations
  lambda_url=$(aws lambda get-function-url-config --function-name "$name" --region "$region" --profile "$profile" --query 'FunctionUrl' --output text 2>/dev/null)
  if [ "$lambda_url" != "None" ] && [ ! -z "$lambda_url" ]; then
    echo "  - Lambda URL: $lambda_url"
  else
    echo "  - No Lambda URL configured."
  fi

  # Check for REST APIs associated with the Lambda function
  rest_apis=$(aws apigateway get-rest-apis --region "$region" --profile "$profile" --query 'items[?name==`'"$name"'`].{id:id, name:name}' --output text)
  if [ "$rest_apis" != "None" ] && [ ! -z "$rest_apis" ]; then
    echo "  - Associated REST API(s):"
    IFS=$'\n'
    for api in $rest_apis; do
      read -ra ADDR <<< "$api"
      api_id=${ADDR[0]}
      api_name=${ADDR[1]}
      stage_names=$(aws apigateway get-stages --rest-api-id "$api_id" --region "$region" --profile "$profile" --query 'item[].stageName' --output text)
      for stage_name in $stage_names; do
        echo "    - API Name: $api_name, Stage: $stage_name, URL: https://${api_id}.execute-api.$region.amazonaws.com/$stage_name"
      done
    done
    unset IFS
  else
    echo "  - No associated REST API(s)."
  fi

  # Check for HTTP APIs associated with the Lambda function
  http_apis=$(aws apigatewayv2 get-apis --region "$region" --profile "$profile" --query 'Items[?Name==`'"$name"'`].{ApiId:ApiId, Name:Name}' --output text)
  if [ "$http_apis" != "None" ] && [ ! -z "$http_apis" ]; then
    echo "  - Associated HTTP API(s):"
    IFS=$'\n'
    for api in $http_apis; do
      read -ra ADDR <<< "$api"
      api_id=${ADDR[0]}
      api_name=${ADDR[1]}
      stage_names=$(aws apigatewayv2 get-stages --api-id "$api_id" --region "$region" --profile "$profile" --query 'Items[].StageName' --output text)
      for stage_name in $stage_names; do
        echo "    - API Name: $api_name, Stage: $stage_name, URL: https://${api_id}.execute-api.$region.amazonaws.com/$stage_name"
      done
    done
    unset IFS
  else
    echo "  - No associated HTTP API(s)."
  fi

  echo "-------------------------------------"
done
