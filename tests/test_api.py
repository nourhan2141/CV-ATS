import requests
import json

url = "http://127.0.0.1:8000/evaluate"
file_path = r"c:\Users\hp\Desktop\cv_ATS\synsetic_data\01_clean_single_column.pdf"

print(f"Sending request to {url} with file {file_path}...")

try:
    with open(file_path, "rb") as f:
        files = {"file": ("01_clean_single_column.pdf", f, "application/pdf")}
        response = requests.post(url, files=files)

    print(f"\nStatus Code: {response.status_code}")
    
    try:
        # Pretty print the JSON response
        result = response.json()
        print("\nResponse:")
        print(json.dumps(result, indent=2))
    except json.JSONDecodeError:
        print("\nResponse Text:")
        print(response.text)
except requests.exceptions.ConnectionError:
    print(f"Failed to connect to {url}. Make sure the Uvicorn server is running!")
