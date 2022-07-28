import json
import requests

def load_credentials():
    with open('credentials.json', 'r') as f:
        return json.load(f)


def main():
    credentials = load_credentials()
    auth = {'Authorization': 'Bearer ' + credentials['access_token']}
    r = requests.get('https://owner-api.teslamotors.com/api/1/energy_sites/194082077326/live_status', headers=auth)    
    print(r.json())

if __name__ == '__main__':
    main()

