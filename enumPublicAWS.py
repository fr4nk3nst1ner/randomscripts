import boto3
import argparse
import sys
import concurrent.futures
from typing import List, Dict
import logging
import json
import csv

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Configure logging"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )

def get_public_amis(profile, accounts_file):
    """Check for public AMIs owned by the accounts in the accounts file."""
    try:
        session = boto3.Session(profile_name=profile)
        ec2 = session.client('ec2')
    except Exception as e:
        print(f"Error initializing AWS session for profile {profile}: {str(e)}")
        sys.exit(1)

    try:
        with open(accounts_file, 'r') as f:
            account_ids = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        print(f"Error: File {accounts_file} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading accounts file: {str(e)}")
        sys.exit(1)

    for account_id in account_ids:
        print(f"\nChecking AMIs for account: {account_id}")
        try:
            response = ec2.describe_images(Owners=[account_id])
            public_amis = [
                image for image in response['Images']
                if image.get('Public', False)
            ]

            if public_amis:
                print(f"Public AMIs found for account {account_id}:")
                for ami in public_amis:
                    print(f"- AMI ID: {ami['ImageId']}, Name: {ami['Name']}, Description: {ami.get('Description', 'N/A')}")
            else:
                print(f"No public AMIs found for account {account_id}.")
        except Exception as e:
            print(f"Error checking account {account_id}: {str(e)}")


def get_public_ebs_snapshots(profile, accounts_file):
    """Check for public EBS snapshots owned by the accounts in the accounts file."""
    try:
        session = boto3.Session(profile_name=profile)
        ec2 = session.client('ec2')
    except Exception as e:
        print(f"Error initializing AWS session for profile {profile}: {str(e)}")
        sys.exit(1)

    try:
        with open(accounts_file, 'r') as f:
            account_ids = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        print(f"Error: File {accounts_file} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading accounts file: {str(e)}")
        sys.exit(1)

    for account_id in account_ids:
        print(f"\nChecking EBS snapshots for account: {account_id}")
        try:
            response = ec2.describe_snapshots(OwnerIds=[account_id])
            public_snapshots = [
                snapshot for snapshot in response['Snapshots']
                if snapshot.get('Public', False)
            ]

            if public_snapshots:
                print(f"Public EBS snapshots found for account {account_id}:")
                for snapshot in public_snapshots:
                    print(f"- Snapshot ID: {snapshot['SnapshotId']}, Description: {snapshot.get('Description', 'N/A')}")
            else:
                print(f"No public EBS snapshots found for account {account_id}.")
        except Exception as e:
            print(f"Error checking account {account_id}: {str(e)}")


def get_public_ecr_repositories(profile, accounts_file):
    """Check for public ECR repositories owned by the accounts in the accounts file."""
    try:
        session = boto3.Session(profile_name=profile)
        ecr = session.client('ecr-public', region_name='us-east-1')  # Public ECR is only available in us-east-1
    except Exception as e:
        print(f"Error initializing AWS session for profile {profile}: {str(e)}")
        sys.exit(1)

    try:
        with open(accounts_file, 'r') as f:
            account_ids = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        print(f"Error: File {accounts_file} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading accounts file: {str(e)}")
        sys.exit(1)

    for account_id in account_ids:
        print(f"\nChecking public ECR repositories for account: {account_id}")
        try:
            # List all public repositories
            paginator = ecr.get_paginator('describe_repositories')
            public_repos = []
            
            for page in paginator.paginate():
                for repo in page['repositories']:
                    if repo.get('registryId') == account_id:
                        public_repos.append(repo)

            if public_repos:
                print(f"Public ECR repositories found for account {account_id}:")
                for repo in public_repos:
                    print(f"- Repository Name: {repo['repositoryName']}")
                    print(f"  URI: {repo['repositoryUri']}")
                    
                    # Get the images in the repository
                    try:
                        images = ecr.describe_images(repositoryName=repo['repositoryName'])
                        if images['imageDetails']:
                            print("  Images:")
                            for image in images['imageDetails']:
                                tags = image.get('imageTags', ['<untagged>'])
                                print(f"    - Tags: {', '.join(tags)}")
                    except Exception as img_error:
                        print(f"  Error listing images: {str(img_error)}")
            else:
                print(f"No public ECR repositories found for account {account_id}.")
        except Exception as e:
            print(f"Error checking account {account_id}: {str(e)}")


def check_account(profile: str, account_id: str, action: str) -> Dict:
    """Handle checks for a single account"""
    try:
        session = boto3.Session(profile_name=profile)
        if action == "ami":
            return check_single_account_amis(session, account_id)
        elif action == "ebs":
            return check_single_account_snapshots(session, account_id)
        elif action == "ecr":
            return check_single_account_ecr(session, account_id)
    except Exception as e:
        return {"account_id": account_id, "error": str(e)}

def run_concurrent_checks(profile: str, account_ids: List[str], action: str, max_workers: int = 10):
    """Run checks concurrently across multiple accounts"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(check_account, profile, account_id, action)
            for account_id in account_ids
        ]
        for future in concurrent.futures.as_completed(futures):
            yield future.result()

def format_output(results: List[Dict], output_format: str, output_file: str = None):
    """Format and output results"""
    if output_format == "json":
        output = json.dumps(results, indent=2)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
        else:
            print(output)
    elif output_format == "csv":
        if output_file:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

def get_regions(session: boto3.Session) -> List[str]:
    """Get list of available regions"""
    ec2 = session.client('ec2')
    regions = [region['RegionName'] for region in ec2.describe_regions()['Regions']]
    return regions

def check_all_regions(session: boto3.Session, account_id: str, action: str) -> List[Dict]:
    """Check resources across all regions for an account"""
    results = []
    for region in get_regions(session):
        if action != "ecr":  # ECR public is only in us-east-1
            results.extend(check_region(session, account_id, action, region))
    return results

def check_resource_tags(session: boto3.Session, resource_id: str, resource_type: str) -> Dict:
    """Check tags for a given resource"""
    client = session.client('resourcegroupstaggingapi')
    try:
        response = client.get_resources(
            ResourceARNList=[resource_id],
            ResourcesPerPage=1
        )
        if response['ResourceTagMappingList']:
            return response['ResourceTagMappingList'][0].get('Tags', {})
    except Exception as e:
        logging.warning(f"Error getting tags for {resource_id}: {str(e)}")
    return {}

def get_organization_accounts(session: boto3.Session) -> List[str]:
    """Get all account IDs in the organization"""
    org_client = session.client('organizations')
    accounts = []
    paginator = org_client.get_paginator('list_accounts')
    
    for page in paginator.paginate():
        for account in page['Accounts']:
            if account['Status'] == 'ACTIVE':
                accounts.append(account['Id'])
    return accounts

def generate_summary(results: List[Dict]) -> Dict:
    """Generate a summary of findings"""
    summary = {
        "total_accounts_checked": len(set(r['account_id'] for r in results)),
        "accounts_with_findings": len(set(r['account_id'] for r in results if r.get('findings'))),
        "total_findings": sum(len(r.get('findings', [])) for r in results),
        "findings_by_type": {},
        "errors": [r['error'] for r in results if 'error' in r]
    }
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AWS utilities for checking public AMIs, EBS snapshots, and ECR repositories.")
    
    # Update choices to include 'ecr'
    parser.add_argument("action", choices=["ami", "ebs", "ecr"], 
                       help="Action to perform: 'ami' to check public AMIs, 'ebs' to check public EBS snapshots, or 'ecr' to check public ECR repositories")
    
    # Optional arguments remain the same
    parser.add_argument("--profile", required=True, help="AWS CLI profile name")
    parser.add_argument("--accounts-file", required=True, help="Path to file containing AWS account IDs")

    # Update argument parser to include logging options
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       help="Set the logging level")
    parser.add_argument("--log-file", help="Optional file to write logs to")

    # Add output format arguments
    parser.add_argument("--output-format", choices=["text", "json", "csv"], 
                       default="text", help="Output format")
    parser.add_argument("--output-file", help="File to write output to")

    # Add region argument
    parser.add_argument("--region", help="Specific region to check (default: all regions)")

    # Add organization support argument
    parser.add_argument("--use-organization", action="store_true",
                       help="Use AWS Organizations to discover accounts")

    args = parser.parse_args()

    if args.action == "ami":
        get_public_amis(args.profile, args.accounts_file)
    elif args.action == "ebs":
        get_public_ebs_snapshots(args.profile, args.accounts_file)
    elif args.action == "ecr":
        get_public_ecr_repositories(args.profile, args.accounts_file)

