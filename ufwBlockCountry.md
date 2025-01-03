# What is this? 

- This is a script designed to ue maxmind db to allowlist only US IP addresses
- It uses UFW and ipset under the hood
- Requires a license with maxmind (free)
- You can use cron to run periodically to continuously update the blocklist 
- Word of caution: if you do use cron, this can be dangerous as it has to run with admin priv 


- `allowlist_usa.sh`

```bash
# Download GeoLite2 City and Country data
wget -O /home/username/geoIpBlock/GeoLite2-Country.tar.gz "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=myLicense&suffix=tar.gz"
wget -O /home/username/geoIpBlock/GeoLite2-Country-CSV.zip --content-disposition --user=myUserID --password=myLicense -O GeoLite2-Country-CSV.zip "https://download.maxmind.com/geoip/databases/GeoLite2-Country-CSV/download?license_key=myLicense&suffix=zip"

# Extract the downloaded files
unzip -o /home/username/geoIpBlock/GeoLite2-Country-CSV.zip
tar -xvzf /home/username/geoIpBlock/GeoLite2-Country.tar.gz

# Create the directory for GeoIP files
mkdir -p /usr/share/GeoIP/

# Move the latest GeoLite2-Country CSV files
LATEST_CSV_DIR=$(ls -td /home/username/geoIpBlock/GeoLite2-Country-CSV*/ | head -n 1)
mv "$LATEST_CSV_DIR/GeoLite2-Country-Blocks-IPv4.csv" /usr/share/GeoIP/ 2>/dev/null || echo "No IPv4 CSV file found in $LATEST_CSV_DIR"
mv "$LATEST_CSV_DIR/GeoLite2-Country-Blocks-IPv6.csv" /usr/share/GeoIP/ 2>/dev/null || echo "No IPv6 CSV file found in $LATEST_CSV_DIR"

# Verify the moved files
echo "CSV files moved to /usr/share/GeoIP/"
ls -l /usr/share/GeoIP/

# Extract US IP ranges using Python
python3 /home/username/geoIpBlock/extract_usa_ips.py

# Define the ipset name and input file
IPSET_NAME="us_ips"
US_IP_RANGES_FILE="/home/username/geoIpBlock/us_ip_ranges.txt"

# Create an ipset if it doesn't exist
sudo ipset create "$IPSET_NAME" hash:net -exist

# Flush previous entries 
sudo ipset flush "$IPSET_NAME" 2>/dev/null || sudo ipset create "$IPSET_NAME" hash:net

# Add IP ranges to the ipset
while read -r ip_range; do
    sudo ipset add "$IPSET_NAME" "$ip_range" -exist
done < "$US_IP_RANGES_FILE"

echo "Added US IP ranges to ipset: $IPSET_NAME"

# Create a UFW rule to allow traffic from the ipset
sudo ufw allow proto tcp from any to any match-set "$IPSET_NAME" src

# Reload UFW to apply the rules
sudo ufw reload

sudo ipset list us_ips

echo "UFW rule applied for ipset: $IPSET_NAME"
```

- `extract_usa_ips.py`

```python
import csv

# Paths to the CSV files
IPv4_CSV = "/usr/share/GeoIP/GeoLite2-Country-Blocks-IPv4.csv"
IPv6_CSV = "/usr/share/GeoIP/GeoLite2-Country-Blocks-IPv6.csv"

def extract_us_ip_ranges(csv_file):
    us_ip_ranges = []
    with open(csv_file, mode="r") as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            if row.get("geoname_id") == "6252001":  # US GeoName ID
                us_ip_ranges.append(row["network"])
    return us_ip_ranges

if __name__ == "__main__":
    # Extract IP ranges from both IPv4 and IPv6 CSV files
    us_ipv4_ranges = extract_us_ip_ranges(IPv4_CSV)
    us_ipv6_ranges = extract_us_ip_ranges(IPv6_CSV)

    # Combine and write to a file
    with open("/home/jstines/geoIpBlock/us_ip_ranges.txt", "w") as file:
        for ip_range in us_ipv4_ranges + us_ipv6_ranges:
            file.write(f"{ip_range}\n")

    print("Extracted all US IP ranges to us_ip_ranges.txt.")
```
