#!/bin/bash

# Interactive bash script that recursively clones the specified directory using specified Github username and token

# read username
echo "Enter GIT Username:"
read USERNAME
export USERNAME
echo

# read token
echo "Enter Github Token:"
echo "ghp_AAAAAAAA..."
read GITHUB_TOKEN
export GITHUB_TOKEN
echo

# read git URL
echo "Enter GIT URL"
echo "URL should be in the following format:"
echo "https://api.github.com/orgs/ORGNAME"
read GIT_URL
export GIT_URL
echo

# fetch the list of repositories
for i in $(curl -sS --header "Authorization: Bearer $GITHUB_TOKEN" \
    --header "X-GitHub-Api-Version: 2022-11-28" "$GIT_URL/repos?" | \
    grep "clone_url" | grep "\.git" | awk '{print $2}' | cut -d '"' -f 2 | sort -u);
do
    # either clone or print the full url including the username and token
    # Remove "https://" from the repository URL and then insert credentials
    clean_url=$(echo "$i" | sed 's|https://||g')
    #echo "https://${USERNAME}:${GITHUB_TOKEN}@${clean_url}"
    git clone "https://$USERNAME:$GITHUB_TOKEN@$clean_url"

done
