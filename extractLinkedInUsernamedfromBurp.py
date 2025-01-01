import json
import re
import xml.etree.ElementTree as ET
import base64
import argparse

def extract_names(decoded_text):
    """Extract first and last names from the decoded text."""
    name_pattern = re.compile(r'"text":"([\w\s]+)","attributesV2":\[\]')
    matches = name_pattern.findall(decoded_text)

    # Split into first and last names
    names = []
    for match in matches:
        parts = match.split()
        if len(parts) == 2:  # Ensure there's exactly one first and one last name
            first_name, last_name = parts
            names.append((first_name, last_name))
    return names

def process_burp_file(filename):
    """Process the Burp XML file to extract names."""
    # Parse the XML file
    try:
        tree = ET.parse(filename)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML file: {e}")
        return []

    # Extract and decode base64 responses
    all_names = []
    for item in root.findall('item'):
        response_element = item.find('response')
        if response_element is not None and response_element.attrib.get('base64') == 'true':
            encoded_data = response_element.text
            try:
                decoded_data = base64.b64decode(encoded_data).decode('utf-8', errors='replace')
                names = extract_names(decoded_data)
                all_names.extend(names)
            except Exception as e:
                print(f"Error decoding base64 data: {e}")
    return all_names

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Extract names from Burp responses.")
    parser.add_argument("--file", required=True, help="Burp file containing the responses")
    args = parser.parse_args()

    # Process the file
    all_names = process_burp_file(args.file)

    # Output the results to a file
    output_file = "names_output.txt"
    with open(output_file, "w") as f:
        for first_name, last_name in all_names:
            f.write(f"{first_name} {last_name}\n")

    print(f"Extracted names saved to {output_file}")

if __name__ == "__main__":
    main()

