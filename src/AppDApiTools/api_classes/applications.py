import json
from cryptography.fernet import Fernet
import requests
import logging
import argparse
from .api_base import ApiBase


class Applications(ApiBase):

    @classmethod
    def get_function_parms(cls, subparser):
        # print('getFunctions')
        functions = [
            'list',

        ]
        class_commands = subparser.add_parser('Applications', help='Applications commands')
        class_commands.add_argument('function', choices=functions, help='The Applications api function to run')
        class_commands.add_argument('--id', help='Specific Applications id or comma list')

        class_commands.add_argument('--input', help='The input template created with the AppDynamics UI')
        class_commands.add_argument('--output', help='The output file.', nargs='?', const='dashboard_name')
        class_commands.add_argument('--prettify', help='Prettify the json output', action='store_true')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--name', help='Set the name of the new dashboard', default=False)
        class_commands.add_argument('--auth', help='The auth scheme.', choices=['key', 'user'], default='key')
        return class_commands

    @classmethod
    def run(cls, args, config):
        app = Applications(config, args)
        if args.function == 'list':
            app.get_app_list()

    def get_app_list(self):
        self.do_verbose_print('Doing Applications List...')
        base_url = self.config['CONTROLLER_INFO']['base_url']
        if self.args.auth == 'user':
            self.do_verbose_print('Doing export with user auth...')
            crypt_key = str.encode(self.config['CONTROLLER_INFO']['key'], 'UTF-8')
            fcrypt = Fernet(crypt_key)
            passwd = fcrypt.decrypt(str.encode(self.config['CONTROLLER_INFO']['psw'], 'UTF-8'))
            auth = (self.config['CONTROLLER_INFO']['user'] + '@' + self.config['CONTROLLER_INFO']['account_name'],
                    passwd)
            headers = None
        else:
            self.do_verbose_print('Doing export with token auth...')
            token = self.get_oauth_token()
            headers = {"Authorization": "Bearer " + token}
            auth = None
        try:
            response = requests.get(base_url+'controller/rest/applications?output=JSON', headers=headers, auth=auth)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'Dashboard api export call returned HTTPError: {err}')
        app_data = response.json()
        self.do_verbose_print(json.dumps(app_data)[0:200]+'...')
        if self.args.output:
            json_obj = json.dumps(app_data)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)

