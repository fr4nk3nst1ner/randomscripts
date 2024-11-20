import os
import subprocess
import requests
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import tarfile

# GitHub API Base URL
BASE_URL = "https://api.github.com"

def get_user_public_repos(username, token=None, max_repo_size_kb=None, no_fork=False, time_limit=None):
    """Fetches all public repositories for a given GitHub user, filtering out those larger than max_repo_size_kb, forked, or older than time_limit if specified."""
    headers = {'Authorization': f'token {token}'} if token else {}
    repos_url = f"https://api.github.com/users/{username}/repos"
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


def get_public_repositories(org_name, token):
    """Retrieve public repositories for the specified organization."""
    headers = {"Authorization": f"token {token}"} if token else {}
    url = f"{BASE_URL}/orgs/{org_name}/repos"
    params = {"type": "public", "per_page": 100}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return [repo['name'] for repo in response.json()]

def get_user_repositories(username, token):
    """Retrieve all repositories for a specific user."""
    headers = {"Authorization": f"token {token}"} if token else {}
    url = f"{BASE_URL}/users/{username}/repos"
    params = {"per_page": 100}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return [repo['clone_url'] for repo in response.json()]

def docker_login(registry, username, token):
    """Log in to the container registry using the Docker CLI."""
    if not username or not token:
        raise ValueError(f"Invalid credentials: username={username}, token={token}")

    try:
        print(f"Logging in to {registry} as {username}...")
        subprocess.run(
            ["docker", "login", registry, "-u", username, "--password-stdin"],
            input=token.encode(),  # Pass the token securely via stdin
            check=True
        )
        print("Login succeeded!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to log in to {registry}: {e}")
        raise

def docker_pull_image(image_name):
    """Pull a Docker image using the Docker CLI."""
    try:
        print(f"Pulling image: {image_name}")
        subprocess.run(
            ["docker", "pull", image_name],
            check=True
        )
        print(f"Image {image_name} pulled successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to pull image {image_name}: {e}")
        raise

def scan_docker_image(image_name, verify=False):
    """Scan a Docker image using trufflehog."""
    try:
        print(f"Scanning image: {image_name}")
        command = ["trufflehog", "docker", "--image", image_name]

        # Append the correct flag based on `verify`
        if verify:
            print("Warning: '--verify' flag not supported by trufflehog.")
            # Remove this append if `--verify` is truly unsupported.
            command.append("--verify")
        else:
            command.append("--no-verification")

        subprocess.run(command, check=True)
        print(f"Scan of {image_name} completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to scan image {image_name}: {e}")
        raise

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

def delete_docker_image(image_name):
    """Delete a Docker image using the Docker CLI."""
    try:
        print(f"Deleting image: {image_name}")
        subprocess.run(
            ["docker", "rmi", image_name],
            check=True
        )
        print(f"Image {image_name} deleted successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to delete image {image_name}: {e}")
        raise

def extract_docker_image_layers(image_name, output_directory):
    """Extract Docker image layers into a specified directory and untar the layers."""
    try:
        # Ensure the output directory exists
        os.makedirs(output_directory, exist_ok=True)

        # Save the Docker image as a tar archive
        tar_path = os.path.join(output_directory, f"{image_name.replace('/', '_')}.tar")
        print(f"Saving Docker image {image_name} to {tar_path}...")
        subprocess.run(["docker", "save", "-o", tar_path, image_name], check=True)

        # Extract the tar archive
        extracted_path = os.path.join(output_directory, image_name.replace("/", "_"))
        os.makedirs(extracted_path, exist_ok=True)
        print(f"Extracting layers from {tar_path} to {extracted_path}...")
        with tarfile.open(tar_path, "r") as tar:
            tar.extractall(path=extracted_path)

        print(f"Layers extracted to {extracted_path}")

        # Untar the layers in blobs/sha256
        layers_path = os.path.join(extracted_path, "blobs", "sha256")
        for layer_file in os.listdir(layers_path):
            layer_path = os.path.join(layers_path, layer_file)
            if tarfile.is_tarfile(layer_path):
                layer_output_path = os.path.join(layers_path, f"untarred_{layer_file}")
                os.makedirs(layer_output_path, exist_ok=True)
                print(f"Extracting layer: {layer_file}")
                with tarfile.open(layer_path, "r") as layer_tar:
                    layer_tar.extractall(path=layer_output_path)
                print(f"Layer extracted to: {layer_output_path}")

    except Exception as e:
        print(f"Failed to extract layers for image {image_name}: {e}")
        raise

def ghcr_main(org_name, token, user=None, repo=None, user_list_file=None, verify=False, retain_image=False, extract_layers=None):
    """Main function for the 'ghcr' command."""
    # Determine the username for authentication
    username = user or (repo.split("/")[-2] if repo else org_name)
    if not username:
        raise ValueError("A valid username or organization must be provided for authentication.")

    # Log in to the registry if a token is provided
    if token:
        docker_login("ghcr.io", username, token)

    # Evaluate specific repo if provided
    if repo:
        print(f"Processing specific repo: {repo}")
        repo_parts = repo.rstrip("/").split("/")
        if len(repo_parts) < 2:
            print(f"Invalid repository URL: {repo}")
            return
        repo_name = repo_parts[-1]
        user_name = repo_parts[-2]

        # Construct the Docker image name
        image_name = f"ghcr.io/{user_name}/{repo_name}:latest"
        docker_pull_image(image_name)

        # Extract layers if requested
        if extract_layers:
            extract_docker_image_layers(image_name, extract_layers)

        # Scan the image if not extracting layers
        else:
            scan_docker_image(image_name, verify)

        # Delete the image unless retain_image is passed
        if not retain_image:
            delete_docker_image(image_name)
        return

    # Evaluate repositories for a specific user
    if user:
        print(f"Processing repositories for user: {user}")
        repos = get_user_repositories(user, token)
        for repo_url in repos:
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            image_name = f"ghcr.io/{user}/{repo_name}:latest"
            docker_pull_image(image_name)
            scan_docker_image(image_name, verify)
            if not retain_image:
                delete_docker_image(image_name)
        return

    # Use provided org_name or fetch user list if specified
    if user_list_file:
        with open(user_list_file, 'r') as f:
            users = [line.strip() for line in f if line.strip()]
        print(f"Using user list from {user_list_file}")
    else:
        users = [org_name]

    for user in users:
        print(f"Processing user/org: {user}")
        public_repos = get_public_repositories(user, token)
        for repo_name in public_repos:
            image_name = f"ghcr.io/{user}/{repo_name}:latest"
            docker_pull_image(image_name)
            scan_docker_image(image_name, verify)
            if not retain_image:
                delete_docker_image(image_name)

def github_main(org_name, token, max_repo_size_mb, user=None, repo=None, user_list_file=None, get_users_file=None, clone=False, trufflehog=False, verify=False, only_verified=False, no_fork=False, time_limit=None):
    """Main function for the 'github' command."""
    max_repo_size_kb = max_repo_size_mb * 1000 if max_repo_size_mb is not None else None  # Convert MB to KB or leave None

    # Evaluate specific repo if provided
    if repo:
        print(f"Processing specific repo: {repo}")
        run_trufflehog([repo], "specified-repo", verify, only_verified)
        return

    # Evaluate repositories for a specific user
    if user:
        print(f"Processing repositories for user: {user}")
        repos = get_user_repositories(user, token)
        run_trufflehog(repos, user, verify, only_verified)
        return

    # Process user list or organization
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
    parser = argparse.ArgumentParser(description="GitHub repository and container scanning utility.")
    parser.add_argument("command", choices=["github", "ghcr"], help="Command to run ('github' or 'ghcr')")
    parser.add_argument("--github-org", help="Name of the GitHub organization (required if --user-list is not provided)")
    parser.add_argument("--max-repo-size", type=int, help="Maximum repository size in MB (no limit if omitted)")
    parser.add_argument("--token", help="GitHub Personal Access Token (optional for public repositories)")
    parser.add_argument("--user", help="Process repositories for a specific user")
    parser.add_argument("--repo", help="Process a specific repository URL")
    parser.add_argument("--user-list", help="File with a list of usernames to process (one per line)")
    parser.add_argument("--get-users", help="File to save the list of organization members (one per line)")
    parser.add_argument("--clone", action="store_true", help="Clone the repositories (only for 'github')")
    parser.add_argument("--trufflehog", action="store_true", help="Run trufflehog on the repositories instead of cloning (only for 'github')")
    parser.add_argument("--verify", action="store_true", help="Run trufflehog with verification (omit --no-verification)")
    parser.add_argument("--only-verified", action="store_true", help="Run trufflehog with --only-verified option")
    parser.add_argument("--no-fork", action="store_true", help="Exclude forked repositories from trufflehog scan or clone")
    parser.add_argument("--time-limit", type=int, help="Limit repositories to those updated within the last N years")
    parser.add_argument("--retain-image", action="store_true", help="Retain the Docker image after scanning")
    parser.add_argument("--extract-layers", help="Directory to extract Docker image layers")

    args = parser.parse_args()

    if args.command == "github":
        if not args.clone and not args.trufflehog:
            parser.error("Either --clone or --trufflehog must be specified for 'github' command.")
        github_main(args.github_org, args.token, args.max_repo_size, args.user, args.repo, args.user_list, args.get_users, args.clone, args.trufflehog, args.verify, args.only_verified, args.no_fork, args.time_limit)
    if args.command == "ghcr":
        if not (args.github_org or args.user_list or args.user or args.repo):
            parser.error("Either --github-org, --user, or --user-list must be specified for 'ghcr' command.")
        ghcr_main(args.github_org, args.token, args.user, args.repo, args.user_list, args.verify, args.retain_image, args.extract_layers)
