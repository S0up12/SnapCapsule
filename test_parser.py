import os
import json
from bs4 import BeautifulSoup

def test_agnostic_parse(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    print(f"--- ANALYZING STRUCTURE ---")
    
    # Strategy 1: Look for modern Div classes
    # Snapchat often uses 'chat-message', 'message-body', or similar
    messages = []
    
    # Try finding all divs and look for a recurring pattern
    all_divs = soup.find_all('div')
    print(f"Total Divs found: {len(all_divs)}")

    # Strategy 2: Look for lists (ul/li)
    all_lis = soup.find_all('li')
    if all_lis: print(f"Total List Items (li) found: {len(all_lis)}")

    # Strategy 3: Just try to find ANY text that looks like a date/name
    # If the rows/tds failed, it means they aren't there.
    # Let's try to print the first 500 characters of the BODY to see the tags
    body_snippet = str(soup.body)[:1000]
    print(f"\n--- HTML Snippet (First 1000 chars of Body) ---")
    print(body_snippet)
    print(f"\n--- END SNIPPET ---")

if __name__ == "__main__":
    target_file = input("Enter path to subpage_*.html: ")
    test_agnostic_parse(target_file)