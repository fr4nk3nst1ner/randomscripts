#!/bin/bash

# Function to clone repositories
clone_repos() {
    local repos=("$@")

    for repo in "${repos[@]}"; do
        repo_name=$(basename "$repo" .git)
        repo_path="$CLONE_DIR/$repo_name"

        # Modify repo URL to include authentication
        auth_repo_url="${repo/https:\/\//https:\/\/$USERNAME:$TOKEN@}"

        if [[ -d "$repo_path" ]]; then
            echo "Repository '$repo_name' already exists, pulling latest changes..."
            git -C "$repo_path" pull
        else
            echo "Cloning '$repo_name'..."
            git clone --recursive "$auth_repo_url" "$repo_path"
        fi
    done
}

# Function to fetch repositories from Gitea
fetch_gitea_repos() {
    local page=1
    local repos=()

    while true; do
        response=$(curl -s -H "Authorization: token $TOKEN" "$GIT_URL/api/v1/orgs/$ORG_NAME/repos?page=$page&limit=50")

        # Check if response is empty or invalid
        if [[ -z "$response" || "$response" == "[]" ]]; then
            break
        fi

        # Extract repository clone URLs
        repo_urls=$(echo "$response" | grep -o '"clone_url":"[^"]*' | cut -d '"' -f 4)

        if [[ -z "$repo_urls" ]]; then
            break
        fi

        repos+=($repo_urls)
        ((page++))
    done

    echo "${repos[@]}"
}

# Function to fetch repositories from GitHub
fetch_github_repos() {
    local repos=()

    repo_urls=$(curl -sS --header "Authorization: Bearer $TOKEN" \
        --header "X-GitHub-Api-Version: 2022-11-28" "$GIT_URL/repos?" | \
        grep "clone_url" | grep "\.git" | awk '{print $2}' | cut -d '"' -f 2 | sort -u)

    for repo in $repo_urls; do
        repos+=("$repo")
    done

    echo "${repos[@]}"
}

# Interactive selection: GitHub or Gitea
echo "Select the Git service to clone from:"
echo "1) GitHub"
echo "2) Gitea"
read -p "Enter choice (1 or 2): " CHOICE

# Common inputs
read -p "Enter your username: " USERNAME
read -s -p "Enter your access token: " TOKEN
echo ""
read -p "Enter the directory to store repositories (default: gitea_repos): " CLONE_DIR
CLONE_DIR=${CLONE_DIR:-gitea_repos}
mkdir -p "$CLONE_DIR"

# Handle user choice
if [[ "$CHOICE" == "1" ]]; then
    echo "You selected GitHub."
    read -p "Enter the GitHub API URL (e.g., https://api.github.com/orgs/ORGNAME): " GIT_URL
    repos=($(fetch_github_repos))

elif [[ "$CHOICE" == "2" ]]; then
    echo "You selected Gitea."
    read -p "Enter the Gitea instance URL (e.g., https://gitea.example.com): " GITEA_URL
    read -p "Enter the Gitea organization name: " ORG_NAME
    GIT_URL="$GITEA_URL"
    repos=($(fetch_gitea_repos))

else
    echo "Invalid choice. Exiting."
    exit 1
fi

# Clone or update repositories
if [[ ${#repos[@]} -gt 0 ]]; then
    echo "Found ${#repos[@]} repositories."
    clone_repos "${repos[@]}"
else
    echo "No repositories found."
fi
