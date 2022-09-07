import json
import csv
import requests


def get_list(base_url, token, application_name, out_file=None):
    headers = {"Authorization": "Bearer "+token}
    response = requests.get(base_url+'controller/rest/applications/'+application_name+'/backends?output=JSON', headers=headers)
    print(response.json())
    if out_file is not None:
        fp = open(out_file, 'w')
        json.dump(response.json(), fp)
    return response.json()

