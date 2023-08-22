import os
import requests
import argparse


'''
This script is used to validate a Databricks API key, list notebooks, and retrieve all notebooks. 
Usage:

python3 notebook_extract.py --token <tokengoeshere> --base-url <https://urlgoeshere/api/2.0> --action test
python3 notebook_extract.py --token <tokengoeshere> --base-url <https://urlgoeshere/api/2.0> --action list
python3 notebook_extract.py --token <tokengoeshere> --base-url <https://urlgoeshere/api/2.0> --action download
'''



def test_authentication(headers, base_url):
    response = requests.get(base_url, headers=headers)

    if response.status_code == 200:
        print("Authentication successful. API token has access to the base URL.")
    else:
        print("Authentication failed. API token does not have access to the base URL.")

def list_notebooks(headers, base_url):
    notebooks_url = base_url + "workspace/list"
    response = requests.get(notebooks_url, headers=headers)

    if response.status_code == 200:
        notebooks = response.json().get("objects", [])
        print("List of Notebooks:")
        for notebook in notebooks:
            print(notebook["path"])
    else:
        print("Failed to fetch notebooks:", response.text)

def export_notebooks(headers, base_url):
    notebooks_url = base_url + "workspace/export"
    response = requests.get(notebooks_url, headers=headers)
    
    if response.status_code == 200:
        notebooks = response.json().get("objects", [])
        for notebook in notebooks:
            notebook_path = notebook["path"]
            notebook_name = os.path.basename(notebook_path)
            export_path = os.path.join("exported_notebooks", notebook_name + ".dbc")
            
            export_payload = {
                "path": notebook_path
            }
            
            export_response = requests.post(notebooks_url, json=export_payload, headers=headers)
            
            if export_response.status_code == 200:
                with open(export_path, "wb") as f:
                    f.write(export_response.content)
                print(f"Notebook '{notebook_name}' exported to '{export_path}'")
            else:
                print(f"Failed to export notebook '{notebook_name}': {export_response.text}")
    else:
        print("Failed to fetch notebooks:", response.text)


def main():
    parser = argparse.ArgumentParser(description="Databricks API Interaction")
    parser.add_argument("--token", required=True, help="Databricks API token")
    parser.add_argument("--action", required=True, choices=["list", "download", "test"], help="Action: list, download, or test")
    parser.add_argument("--base-url", required=True, help="Databricks base URL")
    args = parser.parse_args()

    headers = {
        "Authorization": f"Bearer {args.token}"
    }

    base_url = args.base_url.rstrip("/") + "/api/2.0/"

    if args.action == "test":
        test_authentication(headers, base_url)
    elif args.action == "list":
        list_notebooks(headers, base_url)
    elif args.action == "download":
        if not os.path.exists("exported_notebooks"):
            os.makedirs("exported_notebooks")
        export_notebooks(headers, base_url)

if __name__ == "__main__":
    main()

