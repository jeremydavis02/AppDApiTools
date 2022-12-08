import datetime

import requests
import logging
from cryptography.fernet import Fernet


class ApiBase:
    CONTROLLER_SECTION = 'CONTROLLER_INFO'
    SYNTH_SECTION = 'SYNTH_INFO'
    oath_token = None

    def __init__(self, config, args):
        self.oauth_token = None
        self.config = config
        self.args = args

    def set_config_prefixes(self):
        # TODO test if exists and fail clean if not
        if self.args.system is not None:
            self.CONTROLLER_SECTION = self.args.system + '-CONTROLLER_INFO'
            self.SYNTH_SECTION = self.args.system + '-SYNTH_INFO'

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

        if self.oauth_token is not None and self.oauth_token['expiration_time'] > datetime.datetime.now():
            # fixing function to only get token once expired
            self.do_verbose_print(f'Returning valid current token: {self.oauth_token}')
            return self.oauth_token['access_token']
        self.do_verbose_print(f'Doing get oath token, current token: {self.oauth_token}')
        client_id = self.config[self.CONTROLLER_SECTION]['client_id']
        account_name = self.config[self.CONTROLLER_SECTION]['account_name']
        client_secret = self.config[self.CONTROLLER_SECTION]['client_secret']
        token_url = self.config[self.CONTROLLER_SECTION]['token_url'] + '?output=json'
        headers = {"Content-Type": "application/vnd.appd.cntrl+protobuf;v=1"}
        payload = f'grant_type=client_credentials&client_id={client_id}@{account_name}&client_secret={client_secret}'
        try:
            response = requests.post(token_url, data=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)
        self.do_verbose_print(response)
        self.do_verbose_print(response.text)
        self.oauth_token = response.json()
        self.oauth_token['expiration_time'] = datetime.datetime.now() + \
            datetime.timedelta(seconds=self.oauth_token['expires_in'])
        self.do_verbose_print(self.oauth_token)

        return self.oauth_token['access_token']

    def set_auth_headers(self):
        auth = None
        headers = None
        if self.args.auth == 'user':
            self.do_verbose_print('Doing api call with user auth...')
            crypt_key = str.encode(self.config[self.CONTROLLER_SECTION]['key'], 'UTF-8')
            fcrypt = Fernet(crypt_key)
            passwd = fcrypt.decrypt(str.encode(self.config[self.CONTROLLER_SECTION]['psw'], 'UTF-8'))
            auth = (
            self.config[self.CONTROLLER_SECTION]['user'] + '@' + self.config[self.CONTROLLER_SECTION]['account_name'],
            passwd)
            headers = None
        else:
            self.do_verbose_print('Doing api call with token auth...')
            token = self.get_oauth_token()
            headers = {"Authorization": "Bearer " + token}
            auth = None
        return headers, auth
