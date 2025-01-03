# CloudEnum

Cloud resource enumeration tool. Supports both authenticated API-based enumeration and unauthenticated metadata service enumeration across AWS, GCP, and Azure cloud platforms. Even though it's "unauthenticated", it's still using credentials to enumerate resources.

## Overview

CloudEnum provides two primary modes of operation:
- **Unauthenticated Mode**: For API-based enumeration using cloud credentials
- **Authenticated Mode**: For metadata/runtime service enumeration from within cloud resources

### Supported Platforms and Features

#### AWS
- Unauthenticated Mode (API-based):
  - AMI enumeration
  - EBS snapshot enumeration
  - ECR repository enumeration

- Authenticated Mode (Metadata/Runtime):
  - IMDSv1 enumeration
  - Lambda runtime enumeration
  - Beanstalk environment enumeration
  - CloudFront distribution enumeration

#### GCP
- Unauthenticated Mode:
  - Storage bucket enumeration
  - Compute instance enumeration
  - GKE cluster enumeration
  - Artifact registry enumeration

- Authenticated Mode:
  - Metadata service enumeration

#### Azure
- Unauthenticated Mode:
  - Container registry (ACR) enumeration
  - AKS cluster enumeration

- Authenticated Mode:
  - Instance metadata enumeration

## Installation

```
# Clone the repository
git clone https://github.com/fr4nk3nst1ner/cloudEnum.git

# Change to the directory
cd cloudEnum

# Build the tool
go build
```

## Usage

### Basic Command Structure
```
cloudEnum <auth|unauth> -platform <aws|gcp|azure> -action <action_name> [additional flags]
```

### Required Flags
- `-platform`: Cloud platform to use (aws, gcp, azure)
- `-action`: Action to perform

### Platform-Specific Required Flags
#### AWS
- `-profile`: AWS profile name (required for unauth mode)
- `-accounts-file`: File containing AWS account IDs (required for unauth mode)

#### GCP
- `-project-id`: GCP Project ID (required for unauth mode)

#### Azure
- `-subscription-id`: Azure Subscription ID (required for unauth mode)

### Examples

#### AWS Examples
```
# Enumerate public AMIs
cloudEnum unauth -platform aws -action ami -profile myprofile -accounts-file accounts.txt

# Check for IMDSv1 enabled instances
cloudEnum auth -platform aws -action imdsv1

# Enumerate Lambda functions
cloudEnum auth -platform aws -action lambda
```

#### GCP Examples
```
# Enumerate storage buckets
cloudEnum unauth -platform gcp -action storage -project-id my-project

# Enumerate GKE clusters
cloudEnum auth -platform gcp -action gke -project-id my-project
```

#### Azure Examples
```
# Enumerate ACR repositories
cloudEnum unauth -platform azure -action acr -subscription-id my-subscription

# Enumerate AKS clusters
cloudEnum unauth -platform azure -action aks -subscription-id my-subscription
```

### Additional Options
- `-region`: Specify AWS region (defaults to all regions)
- `-use-organization`: Use AWS Organizations to discover accounts
- `-examples`: Show detailed usage examples

## Use Cases

### 1. Cloud Resource Discovery
- Identify publicly accessible resources
- Enumerate resources across multiple accounts
- Discover potential misconfigurations

### 2. Attack Surface Mapping
- Map out Lambda functions and their triggers
- Identify exposed CloudFront distributions
- Discover container registries and Kubernetes clusters

### 3. Security Assessments
- Check for IMDSv1 usage
- Identify public AMIs and snapshots
- Enumerate service endpoints and APIs

### 4. Multi-Cloud Enumeration
- Consistent interface for AWS, GCP, and Azure
- Standardized output formats
- Efficient resource discovery across platforms


## License
```
MIT License

Copyright (c) 2024 Jonathan Stines

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
