import os
import subprocess
import requests
import argparse
from datetime import datetime, timedelta

def get_org_members(org_name, token=None, output_file=None):
    """Fetches a list of all members in the organization."""
    headers = {'Authorization': f'token {token}'} if token else {}
    members_url = f'https://api.github.com/orgs/{org_name}/members'
    members = []
    page = 1

    while True:
        response = requests.get(members_url, headers=headers, params={'page': page, 'per_page': 100})
        response_data = response.json()

        if response.status_code != 200:
            print(f"Error fetching members: {response_data.get('message', 'Unknown error')}")
            break

        if not response_data:
            break  # Exit loop if no more members

        for member in response_data:
            members.append(member['login'])

        page += 1  # Increment page number for the next set of results

    print(f"Fetched {len(members)} members from {org_name}.")

    # If output file is specified, save the members to the file
    if output_file:
        with open(output_file, 'w') as f:
            for member in members:
                f.write(f"{member}\n")
        print(f"Member list saved to {output_file}")

    return members

def get_user_public_repos(username, token=None, max_repo_size_kb=None, no_fork=False, time_limit=None):
    """Fetches all public repositories for a given GitHub user, filtering out those larger than max_repo_size_kb, forked, or older than time_limit if specified."""
    headers = {'Authorization': f'token {token}'} if token else {}
    repos_url = f'https://api.github.com/users/{username}/repos'
    repos = []
    page = 1

    # Calculate the time limit as a cutoff date
    cutoff_date = None
    if time_limit:
        cutoff_date = datetime.now() - timedelta(days=time_limit * 365)

    while True:
        response = requests.get(repos_url, headers=headers, params={'page': page, 'per_page': 100})
        response_data = response.json()

        if response.status_code != 200:
            print(f"Error fetching repositories for {username}: {response_data.get('message', 'Unknown error')}")
            break

        if not response_data:
            break  # Exit loop if no more repos

        for repo in response_data:
            # Skip forked repos if --no-fork is specified
            if no_fork and repo['fork']:
                print(f"Skipping forked repo {repo['name']} for user {username}")
                continue

            # Skip repos older than the cutoff date if time_limit is specified
            repo_updated_at = datetime.strptime(repo['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
            if cutoff_date and repo_updated_at < cutoff_date:
                print(f"Skipping old repo {repo['name']} (last updated: {repo_updated_at}) for user {username}")
                continue

            # Check if repo size is within the limit, if a max size is specified
            if not repo['private'] and (max_repo_size_kb is None or repo['size'] <= max_repo_size_kb):
                repos.append(repo['clone_url'])
            elif max_repo_size_kb is not None and repo['size'] > max_repo_size_kb:
                print(f"Skipping {repo['name']} for user {username} (size: {repo['size'] / 1000:.2f} MB)")

        page += 1

    size_info = f"under {max_repo_size_kb / 1000:.2f} MB" if max_repo_size_kb else "of any size"
    print(f"Found {len(repos)} public repositories {size_info} for user {username}.")
    return repos

def clone_repos(repos, username):
    """Clones all repositories in the list into a directory named after the user."""
    user_dir = f"./{username}_repos"
    os.makedirs(user_dir, exist_ok=True)

    for repo_url in repos:
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(user_dir, repo_name)

        if not os.path.exists(repo_path):
            print(f"Cloning {repo_name} for user {username}...")
            subprocess.run(["git", "clone", repo_url, repo_path])
        else:
            print(f"Repository {repo_name} already cloned.")

def run_trufflehog(repos, username, verify, only_verified):
    """Runs trufflehog on all repositories in the list, with options for verification."""
    for repo_url in repos:
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        print(f"Running trufflehog on {repo_name} for user {username}...")

        # Build the trufflehog command with options based on verify and only_verified flags
        trufflehog_cmd = ["trufflehog", "git", repo_url]

        if only_verified:
            trufflehog_cmd.append("--only-verified")
        elif not verify:
            trufflehog_cmd.append("--no-verification")

        subprocess.run(trufflehog_cmd)

def main(command, org_name, token, max_repo_size_mb, user_list_file=None, get_users_file=None, clone=False, trufflehog=False, verify=False, only_verified=False, no_fork=False, time_limit=None):
    if command != "github":
        print(f"Unsupported command: {command}")
        return

    max_repo_size_kb = max_repo_size_mb * 1000 if max_repo_size_mb is not None else None  # Convert MB to KB or leave None

    # If user list file is provided, use it, otherwise fetch members from the organization
    if user_list_file:
        with open(user_list_file, 'r') as f:
            members = [line.strip() for line in f if line.strip()]
        print(f"Using user list from {user_list_file}")
    else:
        if not org_name:
            print("Error: --github-org is required if --user-list is not provided.")
            return
        members = get_org_members(org_name, token, output_file=get_users_file)

    for username in members:
        print(f"\nGetting public repos for user {username}...")
        repos = get_user_public_repos(username, token, max_repo_size_kb, no_fork, time_limit)

        if clone:
            clone_repos(repos, username)

        if trufflehog:
            run_trufflehog(repos, username, verify, only_verified)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub repository management and scanning utility.")
    parser.add_argument("command", choices=["github"], help="Command to run (e.g., 'github')")
    parser.add_argument("--github-org", help="Name of the GitHub organization (required if --user-list is not provided)")
    parser.add_argument("--max-repo-size", type=int, help="Maximum repository size in MB (no limit if omitted)")
    parser.add_argument("--token", help="GitHub Personal Access Token (optional for public repositories)")
    parser.add_argument("--user-list", help="File with a list of usernames to process (one per line)")
    parser.add_argument("--get-users", help="File to save the list of organization members (one per line)")
    parser.add_argument("--clone", action="store_true", help="Clone the repositories")
    parser.add_argument("--trufflehog", action="store_true", help="Run trufflehog on the repositories instead of cloning")
    parser.add_argument("--verify", action="store_true", help="Run trufflehog with verification (omit --no-verification)")
    parser.add_argument("--only-verified", action="store_true", help="Run trufflehog with --only-verified option")
    parser.add_argument("--no-fork", action="store_true", help="Exclude forked repositories from trufflehog scan or clone")
    parser.add_argument("--time-limit", type=int, help="Limit repositories to those updated within the last N years")

    args = parser.parse_args()

    # Check for required actions
    if args.command == "github" and not args.clone and not args.trufflehog:
        parser.error("Either --clone or --trufflehog must be specified for 'github' command.")

    main(args.command, args.github_org, args.token, args.max_repo_size, args.user_list, args.get_users, args.clone, args.trufflehog, args.verify, args.only_verified, args.no_fork, args.time_limit)
