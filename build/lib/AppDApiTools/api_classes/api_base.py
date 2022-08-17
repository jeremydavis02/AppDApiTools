import requests

class ApiBase:
    def __init__(self, config, args):
        self.config = config
        self.args = args

    def get_oauth_token(self):
        # print(token_url)
        client_id = self.config['CONTROLLER_INFO']['client_id']
        account_name = self.config['CONTROLLER_INFO']['account_name']
        client_secret = self.config['CONTROLLER_INFO']['client_secret']
        token_url = self.config['CONTROLLER_INFO']['token_url']
        headers = {"Content-Type": "application/vnd.appd.cntrl+protobuf;v=1"}
        payload = f'grant_type=client_credentials&client_id={client_id}@{account_name}&client_secret={client_secret}'
        response = requests.post(token_url, data=payload, headers=headers)
        token = response.json()['access_token']
        print(token)
        return token