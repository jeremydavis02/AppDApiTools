import requests
import logging
import argparse

def get_app_list(token, base_url):
    headers = {"Authorization": "Bearer "+token}
    response = requests.get(base_url+'controller/rest/applications?output=JSON', headers=headers)
    print(response.json())