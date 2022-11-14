import json
import sys

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
            'get'
        ]
        class_commands = subparser.add_parser('Applications', help='Applications commands')
        class_commands.add_argument('function', choices=functions, help='The Applications api function to run')
        class_commands.add_argument('--id', help='Specific Applications id or comma list')
        class_commands.add_argument('--system', help='Specific system prefix config to use')
        class_commands.add_argument('--input', help='The input template created with the AppDynamics UI')
        class_commands.add_argument('--output', help='The output file.', nargs='?', const='dashboard_name')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--name', help='Set the name of the application')
        class_commands.add_argument('--auth', help='The auth scheme.', choices=['key', 'user'], default='key')
        return class_commands

    @classmethod
    def run(cls, args, config):
        app = Applications(config, args)
        app.set_config_prefixes()
        if args.function == 'list':
            app.get_app_list()
        if args.function == 'get':
            app.get_app()

    def get_app(self):
        self.do_verbose_print('Doing Applications Get...')

        if self.args.name is None and self.args.id is None:
            print(f'Application get requires --name or --id, see --help')
            sys.exit()
        output_reset = self.args.output
        self.args.output = None
        app_list = self.get_app_list()
        app_element = {}
        for app in app_list:
            if self.args.id:
                if app["id"] == self.args.id:
                    app_element = app
                    break
            else:
                if app["name"] == self.args.name:
                    app_element = app
                    break
        self.do_verbose_print(json.dumps(app_element)[0:200] + '...')
        self.args.output = output_reset
        if self.args.output:
            json_obj = json.dumps(app_element)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving app data to {self.args.output}')
                outfile.write(json_obj)
        return app_element

    def get_app_list(self):
        self.do_verbose_print('Doing Applications List...')
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        if self.args.auth == 'user':
            self.do_verbose_print('Doing export with user auth...')
            crypt_key = str.encode(self.config[self.CONTROLLER_SECTION]['key'], 'UTF-8')
            fcrypt = Fernet(crypt_key)
            passwd = fcrypt.decrypt(str.encode(self.config[self.CONTROLLER_SECTION]['psw'], 'UTF-8'))
            auth = (self.config[self.CONTROLLER_SECTION]['user'] + '@' + self.config[self.CONTROLLER_SECTION]['account_name'],
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
        return app_data
