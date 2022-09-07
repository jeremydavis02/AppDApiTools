import requests
import logging


class ApiBase:
    def __init__(self, config, args):
        self.config = config
        self.args = args

    def do_verbose_print(self, msg):
        if self.args.verbose:
            print(msg)

    def set_request_logging(self):
        if self.args.verbose:
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
        else:
            logging.basicConfig()
            logging.getLogger().setLevel(logging.CRITICAL)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.CRITICAL)
            requests_log.propagate = True

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

        return token


