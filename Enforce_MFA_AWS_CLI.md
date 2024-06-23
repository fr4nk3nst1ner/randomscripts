# Enforcing MFA for AWS CLI Access

These are the steps that can be used to enforce Multi-Factor Authentication (MFA) for AWS CLI access using an IAM policy attached to a user.

## Step 1: Create an IAM Policy

Create an IAM policy that denies access to AWS CLI commands unless MFA is used.

- Policy JSON

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Deny",
            "Action": "*",
            "Resource": "*",
            "Condition": {
                "BoolIfExists": {
                    "aws:MultiFactorAuthPresent": "false"
                }
            }
        }
    ]
}
```

### Create Policy via AWS Management Console

1. Open the IAM console.
2. Select "Policies" and then "Create policy".
3. Choose the "JSON" tab and paste the policy JSON above.
4. Review the policy and give it a name, e.g., `EnforceMFAPolicy`.
5. Create the policy.

### Create Policy via AWS CLI

Save the policy JSON in a file named `enforce-mfa-policy.json` and run:

```
aws iam create-policy --policy-name EnforceMFAPolicy --policy-document file://enforce-mfa-policy.json --profile PROFILE
```

## Step 2: Attach the Policy to a User

Attach the newly created policy to the IAM user for which you want to enforce MFA.

### Attach Policy via AWS Management Console

1. Go to the IAM console.
2. Select "Users" and choose the user you want to enforce MFA for.
3. Go to the "Permissions" tab and click "Add permissions".
4. Select "Attach policies directly".
5. Select the `EnforceMFAPolicy` and attach it.

### Attach Policy via AWS CLI

```
aws iam attach-user-policy --user-name YourUserName --policy-arn arn:aws:iam::ACCOUNTID:policy/EnforceMFAPolicy --profile PROFILE
```

Replace `YourUserName` with the name of the IAM user.

## Step 3: Configure AWS CLI to Use MFA

Configure the AWS CLI to use an MFA token when making API requests.

### AWS CLI Configuration Files

#### `~/.aws/config`

```
[default]
region = us-west-2
output = json

[profile PROFILE]
region = us-east-1
output = json

[profile PROFILEMFA]
region = us-east-1
output = json
cli_pager = 
```

#### `~/.aws/credentials`

```
[PROFILE]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

Replace `YOUR_ACCESS_KEY_ID` and `YOUR_SECRET_ACCESS_KEY` with your actual AWS access key ID and secret access key for the `PROFILE` profile.

### AWS Login Function for `~/.zshrc`

Add the following function to your `~/.zshrc` file to automatically set AWS credentials when supplying the MFA token:

```
source $HOME/.aws/sts
export MFA_ARN="arn:aws:iam::ACCOUNTID:mfa/DEVICENAME"

function aws-reload {
    source $HOME/.aws/sts
}

aws-reload

function aws-login {
    printf "Enter your MFA code: "
    read gac
    if ! printf "$gac\n" | grep -q '^[[:digit:]]\{6\}$'; then
        printf "Invalid MFA code."
        return 1
    fi
    # If these vars are set the aws sts call will fail
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SECURITY_TOKEN AWS_SESSION_TOKEN AWS_TOKEN_EXPIRATION
    session=$(aws sts get-session-token --profile PROFILE --serial-number arn:aws:iam::ACCOUNTID:mfa/DEVICENAME --token-code $gac | jq '.Credentials')

    echo "export AWS_ACCESS_KEY_ID=$(echo $session | jq -r '.AccessKeyId')" > $HOME/.aws/sts
    echo "export AWS_SECRET_ACCESS_KEY=$(echo $session | jq -r '.SecretAccessKey')" >> $HOME/.aws/sts
    echo "export AWS_SESSION_TOKEN=$(echo $session | jq -r '.SessionToken')" >> $HOME/.aws/sts
    echo "export AWS_TOKEN_EXPIRATION=$(echo $session | jq -r '.Expiration')" >> $HOME/.aws/sts

    # Set the AWS CLI profile to use the temporary credentials
    aws configure set aws_access_key_id "$(echo $session | jq -r '.AccessKeyId')" --profile PROFILEMFA
    aws configure set aws_secret_access_key "$(echo $session | jq -r '.SecretAccessKey')"  --profile PROFILEMFA
    aws configure set aws_session_token "$(echo $session | jq -r '.SessionToken')" --profile PROFILEMFA

    source $HOME/.aws/sts

    if [[ -z "$AWS_TOKEN_EXPIRATION" ]]; then
        printf "\nCould not create session\n"
        return 1
    else
        printf "\nYour session expires on %s\n" $AWS_TOKEN_EXPIRATION
        printf "\nAWS CLI is now configured to use the 'PROFILE' profile with MFA.\n"
        return 0
    fi
}
```

### Using the `aws-login` Function

1. Add the `aws-login` function to your `~/.zshrc` file.
2. Source your `~/.zshrc` file to apply the changes:

   ```
   source ~/.zshrc
   ```

3. Run the `aws-login` function and enter your MFA code when prompted:

   ```
   aws-login
   ```

This will set your AWS CLI to use the temporary session credentials with MFA.

## Step 4: Verify Policy Enforcement

### Using IAM Policy Simulator

1. Open the IAM Policy Simulator: [IAM Policy Simulator](https://policysim.aws.amazon.com/home/index.jsp?#).
2. Select "Users" and choose your user.
3. Add the custom policy and simulate actions to ensure they are denied without MFA and allowed with MFA.

### Direct Testing

1. **Without MFA:**

   ```
   aws s3 ls --profile PROFILE
   ```

   You should see an access denied error.

2. **With MFA (using `aws-login` function):**

- The `aws-login` function assigns the values to the AWS credentials variables in your environment, so you do not need to use the `--profile PROFILE` option after running the function. 

   ```
   aws-login
   aws s3 ls 
   ```

   You should see the list of your S3 buckets if the MFA is correctly configured (assuming your user has s3 list permissions.
