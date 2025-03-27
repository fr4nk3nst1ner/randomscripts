#!/usr/bin/env python3
import os
import markdown
import argparse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import json
import sys
import uuid

"""
Script for creating slides in both html as well as google slides. 
If you use google slides, need to create credentials.json as a desktop app and store in same dir as the script. 
"""

class SlideConverter:
    def __init__(self, markdown_file, output_dir):
        self.SCOPES = ['https://www.googleapis.com/auth/presentations']
        self.markdown_file = markdown_file
        self.output_dir = output_dir
        self.html_output = os.path.join(output_dir, 'presentation.html')

        self.reveal_template = '''
<!doctype html>
<html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Presentation</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/theme/white.min.css">
    </head>
    <body>
        <div class="reveal">
            <div class="slides">
                {slides}
            </div>
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.js"></script>
        <script>
            Reveal.initialize();
        </script>
    </body>
</html>
'''

    def markdown_to_reveal(self):
        """Convert markdown to Reveal.js HTML slides"""
        os.makedirs(self.output_dir, exist_ok=True)

        with open(self.markdown_file, 'r') as f:
            content = f.read()

        slides = content.split('---')
        
        html_slides = []
        for slide in slides:
            if slide.strip():
                slide_html = markdown.markdown(slide.strip())
                html_slides.append(f'<section>{slide_html}</section>')

        all_slides = '\n'.join(html_slides)
        final_html = self.reveal_template.format(slides=all_slides)
        
        with open(self.html_output, 'w') as f:
            f.write(final_html)
        
        return self.html_output

    def check_credentials_file(self):
        """Check if credentials.json exists and is valid"""
        if not os.path.exists('credentials.json'):
            print("Error: credentials.json not found!")
            print("\nTo get credentials.json:")
            print("1. Go to https://console.cloud.google.com/")
            print("2. Create a project or select existing project")
            print("3. Enable Google Slides API:")
            print("   - Go to APIs & Services > Library")
            print("   - Search for 'Google Slides API'")
            print("   - Click Enable")
            print("4. Configure OAuth consent screen:")
            print("   - Go to APIs & Services > OAuth consent screen")
            print("   - Set user type to External")
            print("   - Add scope: .../auth/presentations")
            print("   - Add your email as test user")
            print("   - You can ignore the 'Unverified App' warning - this is normal for development")
            print("5. Create credentials:")
            print("   - Go to APIs & Services > Credentials")
            print("   - Create OAuth client ID")
            print("   - Application type: Desktop application")
            print("   - Add authorized redirect URIs:")
            print("     * http://localhost:8080/")
            print("     * http://localhost/")
            print("6. Download and rename to credentials.json")
            print("\nNote: When you first run the script, you'll see a warning about")
            print("'Google hasn't verified this app'. This is normal for development.")
            print("Click 'Continue' to proceed.")
            sys.exit(1)

    def get_google_credentials(self):
        """Get or create Google API credentials"""
        self.check_credentials_file()
        
        creds = None
        token_path = os.path.join(self.output_dir, 'token.pickle')
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing credentials: {str(e)}")
                    os.remove(token_path)
                    return self.get_google_credentials()
            else:
                try:
                    # More explicit OAuth configuration
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json',
                        scopes=self.SCOPES,
                        redirect_uri='http://localhost:8080/'  # Explicitly set redirect URI
                    )
                    
                    # Configure the local server
                    flow.run_local_server(
                        host='localhost',
                        port=8080,
                        authorization_prompt_message='Please visit this URL to authorize this application: {url}',
                        success_message='The authentication flow has completed. You may close this window.',
                        open_browser=True
                    )
                    
                    # Get credentials
                    creds = flow.credentials
                    
                except Exception as e:
                    print("\nError during authentication:")
                    print(f"Detailed error: {str(e)}")
                    print("\nPlease check:")
                    print("1. Your credentials.json is properly configured")
                    print("2. The OAuth consent screen includes the correct scope:")
                    print("   - https://www.googleapis.com/auth/presentations")
                    print("3. Your OAuth client ID settings include these exact redirect URIs:")
                    print("   - http://localhost:8080/")
                    print("   - http://localhost:8080")
                    print("\nTo fix this:")
                    print("1. Go to Google Cloud Console > APIs & Services > Credentials")
                    print("2. Edit your OAuth Client ID")
                    print("3. Under 'Authorized redirect URIs', add both:")
                    print("   - http://localhost:8080/")
                    print("   - http://localhost:8080")
                    print("4. Click Save and download new credentials")
                    print("5. Replace your credentials.json with the new one")
                    sys.exit(1)
                    
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds

    def create_google_slides(self):
        """Convert HTML presentation to Google Slides"""
        try:
            creds = self.get_google_credentials()
            service = build('slides', 'v1', credentials=creds)

            # Get presentation title from markdown filename
            title = os.path.splitext(os.path.basename(self.markdown_file))[0]

            # Create new presentation
            presentation = service.presentations().create(
                body={'title': title}
            ).execute()
            presentation_id = presentation['presentationId']

            # Delete the default slide
            default_slide = service.presentations().get(
                presentationId=presentation_id
            ).execute()
            if 'slides' in default_slide:
                service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={
                        'requests': [{
                            'deleteObject': {
                                'objectId': default_slide['slides'][0]['objectId']
                            }
                        }]
                    }
                ).execute()

            # Read markdown content
            with open(self.markdown_file, 'r') as f:
                content = f.read()

            # Split into slides and remove empty ones
            slides = [slide.strip() for slide in content.split('---') if slide.strip()]
            
            # Prepare batch update requests
            requests = []
            
            for slide_content in slides:
                # Convert markdown to plain text
                lines = slide_content.split('\n')
                
                # Extract title and body
                title_text = ""
                body_text = ""
                has_bullets = False
                current_list_type = None  # None, 'bullet', or 'number'
                indent_level = 0
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        body_text += '\n'
                        continue
                    
                    if line.startswith('#'):
                        if not title_text:  # Only use the first heading as title
                            title_text = line.lstrip('#').strip()
                    else:
                        # Check for numbered list
                        if line.lstrip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '0.')):
                            number_text = line.lstrip().split('.', 1)[1].strip()
                            body_text += number_text + '\n'
                            has_bullets = True
                            current_list_type = 'number'
                        # Check for bullet list
                        elif line.startswith('- '):
                            body_text += line[2:] + '\n'
                            has_bullets = True
                            current_list_type = 'bullet'
                        elif line.startswith('  - '):
                            body_text += '    ' + line[4:] + '\n'
                            has_bullets = True
                            current_list_type = 'bullet'
                        else:
                            if current_list_type:
                                body_text += '\n'  # Add extra line break before non-list content
                            current_list_type = None
                            body_text += line + '\n'

                # Create a new slide
                slide_id = str(uuid.uuid4())
                requests.append({
                    'createSlide': {
                        'objectId': slide_id,
                        'slideLayoutReference': {
                            'predefinedLayout': 'TITLE_AND_BODY'
                        },
                        'placeholderIdMappings': [
                            {
                                'layoutPlaceholder': {
                                    'type': 'TITLE'
                                },
                                'objectId': f'{slide_id}_title'
                            },
                            {
                                'layoutPlaceholder': {
                                    'type': 'BODY'
                                },
                                'objectId': f'{slide_id}_body'
                            }
                        ]
                    }
                })

                # Add title text
                if title_text:
                    requests.append({
                        'insertText': {
                            'objectId': f'{slide_id}_title',
                            'text': title_text
                        }
                    })

                # Add body text
                if body_text:
                    requests.append({
                        'insertText': {
                            'objectId': f'{slide_id}_body',
                            'text': body_text.strip()
                        }
                    })

                    # Add bullet points if needed
                    if has_bullets:
                        requests.append({
                            'createParagraphBullets': {
                                'objectId': f'{slide_id}_body',
                                'textRange': {
                                    'type': 'ALL'
                                },
                                'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                            }
                        })

            # Execute all requests in one batch
            if requests:
                service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': requests}
                ).execute()

            # Save presentation info
            presentation_info = {
                'presentation_id': presentation_id,
                'url': f"https://docs.google.com/presentation/d/{presentation_id}"
            }
            
            info_file = os.path.join(self.output_dir, 'presentation_info.json')
            with open(info_file, 'w') as f:
                json.dump(presentation_info, f, indent=2)

            print(f"Created Google Slides presentation with ID: {presentation_id}")
            print(f"Access it at: {presentation_info['url']}")
            return presentation_id
            
        except HttpError as e:
            print(f"Google API Error: {str(e)}")
            if "invalid_grant" in str(e):
                print("\nAuthentication failed. Trying to reauthenticate...")
                token_path = os.path.join(self.output_dir, 'token.pickle')
                if os.path.exists(token_path):
                    os.remove(token_path)
                return self.create_google_slides()
            sys.exit(1)
        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Convert markdown slides to Reveal.js and optionally Google Slides')
    parser.add_argument('--slides', required=True, help='Path to the markdown slides file')
    parser.add_argument('--output', required=True, help='Output directory for generated files')
    parser.add_argument('--gslides', action='store_true', help='Also convert to Google Slides')
    
    args = parser.parse_args()
    
    converter = SlideConverter(args.slides, args.output)
    
    print("Converting to Reveal.js HTML...")
    html_file = converter.markdown_to_reveal()
    print(f"Created Reveal.js presentation at: {html_file}")
    
    if args.gslides:
        print("\nConverting to Google Slides...")
        try:
            presentation_id = converter.create_google_slides()
        except Exception as e:
            print(f"Error creating Google Slides: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    main() 
