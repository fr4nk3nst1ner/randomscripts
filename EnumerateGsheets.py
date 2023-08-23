import os
import json
import google.auth
import argparse
from googleapiclient.discovery import build
import gspread

# Load the service account credentials from JSON key file
SERVICE_ACCOUNT_JSON = 'key.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = SERVICE_ACCOUNT_JSON

# Initialize the Google Drive API
credentials, _ = google.auth.default()
drive_api = build('drive', 'v3', credentials=credentials)

# Initialize the Google Sheets API
sheets_api = build('sheets', 'v4', credentials=credentials)

# Initialize gspread for retrieving worksheet content
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
gspread_credentials = gspread.service_account(filename=SERVICE_ACCOUNT_JSON)

# Command-line argument parsing
parser = argparse.ArgumentParser(description="Google Sheets Management Script")
parser.add_argument('--list-worksheet-files', action='store_true', help="List worksheet file names")
parser.add_argument('--list-sheets', action='store_true', help="List sheets contained in the specified worksheet file")
parser.add_argument('--spreadsheet-name', metavar="SPREADSHEET_NAME", help="Specify the name of the spreadsheet for --list-sheets and --get-content")
parser.add_argument('--get-content', action='store_true', help="Retrieve the contents of a specified worksheet")
parser.add_argument('--worksheet-name', metavar="WORKSHEET_NAME", help="Specify the name of the worksheet for --get-content")
args = parser.parse_args()

def list_worksheet_files():
    # List all spreadsheets accessible by the service account
    spreadsheet_list = drive_api.files().list(q="mimeType='application/vnd.google-apps.spreadsheet'").execute()

    # Print the names of all accessible spreadsheets
    for spreadsheet in spreadsheet_list.get('files', []):
        print("Spreadsheet Name:", spreadsheet['name'])

def list_sheets(spreadsheet_name):
    # Search for the spreadsheet by name
    spreadsheet_list = drive_api.files().list(q=f"name='{spreadsheet_name}' and mimeType='application/vnd.google-apps.spreadsheet'").execute()
    spreadsheets = spreadsheet_list.get('files', [])

    if not spreadsheets:
        print(f"No spreadsheet found with the name '{spreadsheet_name}'")
        return

    spreadsheet = spreadsheets[0]
    spreadsheet_id = spreadsheet['id']
    spreadsheet_name = spreadsheet['name']

    print("Spreadsheet Name:", spreadsheet_name)

    # Retrieve sheets within the current spreadsheet
    sheets_metadata = sheets_api.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in sheets_metadata['sheets']:
        sheet_title = sheet['properties']['title']
        print("  Sheet Name:", sheet_title)

def get_content(spreadsheet_name, worksheet_name):
    spreadsheet = gspread_credentials.open(spreadsheet_name)
    worksheet = spreadsheet.worksheet(worksheet_name)
    content = worksheet.get_all_values()
    for row in content:
        print("\t".join(row))

if __name__ == '__main__':
    if args.list_worksheet_files:
        list_worksheet_files()
    elif args.list_sheets and args.spreadsheet_name:
        list_sheets(args.spreadsheet_name)
    elif args.get_content and args.spreadsheet_name and args.worksheet_name:
        get_content(args.spreadsheet_name, args.worksheet_name)
    else:
        parser.print_help()
