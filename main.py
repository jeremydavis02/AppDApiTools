import pkgutil
import importlib
import requests
import logging
import argparse
import configparser
from api_classes import api_base
from api_classes import synthetics


config = configparser.ConfigParser()
config.read('config.ini')

client_id = config['CONTROLLER_INFO']['client_id']
account_name = config['CONTROLLER_INFO']['account_name']
client_secret = config['CONTROLLER_INFO']['client_secret']
token_url = config['CONTROLLER_INFO']['token_url']
base_url = config['CONTROLLER_INFO']['base_url']

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press ⌘F8 to toggle the breakpoint.


def get_oauth_token():
    #print(token_url)
    headers = {"Content-Type": "application/vnd.appd.cntrl+protobuf;v=1"}
    payload = f'grant_type=client_credentials&client_id={client_id}@{account_name}&client_secret={client_secret}'
    response = requests.post(token_url, data=payload, headers=headers)
    token = response.json()['access_token']
    print(token)
    return token





if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AppDynamics API Tooling.')
    for (module_loader, name, ispkg) in pkgutil.iter_modules(['./api_classes']):
        importlib.import_module('.' + name, 'api_classes')

    all_my_base_classes = {cls.__name__: cls for cls in api_base.ApiBase.__subclasses__()}
    print(all_my_base_classes)
    sub_parser = parser.add_subparsers(dest='subparser_name', help='sub commands help')
    for k, v in all_my_base_classes.items():
        mods = importlib.import_module('api_classes.'+k.lower())
        print(mods)
        c = getattr(mods, k)
        c.get_function_parms(sub_parser)



    args = parser.parse_args()
    api_class_ref = getattr(importlib.import_module('api_classes.'+args.subparser_name.lower()), args.subparser_name)
    print(args.subparser_name)
    t = get_oauth_token()
    api_class_ref.run(args, config)

