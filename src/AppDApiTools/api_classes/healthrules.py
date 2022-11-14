import json
import sys

from cryptography.fernet import Fernet
import requests
import logging
import argparse
from .api_base import ApiBase


class Healthrules(ApiBase):

    @classmethod
    def get_function_parms(cls, subparser):
        # print('getFunctions')
        functions = [
            'list',
            'get'
        ]
        class_commands = subparser.add_parser('Healthrules', help='Healthrules commands')
        class_commands.add_argument('function', choices=functions, help='The Healthrules api function to run')
        class_commands.add_argument('--application', help='Specific Applications id or name')
        class_commands.add_argument('--system', help='Specific system prefix config to use')
        class_commands.add_argument('--input', help='The input template created with the AppDynamics UI')
        class_commands.add_argument('--output', help='The output file.', nargs='?', const='dashboard_name')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--name', help='Health Rule name')
        class_commands.add_argument('--id', help='Health Rule id')
        class_commands.add_argument('--auth', help='The auth scheme.', choices=['key', 'user'], default='key')
        return class_commands

    @classmethod
    def run(cls, args, config):
        app = Healthrules(config, args)
        app.set_config_prefixes()
        if args.function == 'list':
            app.get_health_list()
        if args.function == 'get':
            app.get_rule()

    def get_health_list(self):
        # GET <controller_url>/controller/alerting/rest/v1/applications/<application_id>/health-rules
        self.set_request_logging()
        self.do_verbose_print('Doing health rule List...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        url = f'controller/alerting/rest/v1/applications/{self.args.application}/health-rules?output=JSON'
        headers, auth = self.set_auth_headers()
        try:
            #response = requests.get(url, headers=headers)
            response = requests.get(base_url+url, auth=auth, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'Health Rule api export call returned HTTPError: {err}')
        rule_data = response.json()
        self.do_verbose_print(json.dumps(rule_data)[0:200] + '...')
        json_obj = json.dumps(rule_data)
        if self.args.output:
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return rule_data

    def _get_rule_id(self, rule_name=None):
        rule_list = self.get_health_list()
        for rule in rule_list:
            if rule_name == rule["name"]:
                return rule["id"]

    def get_rule(self):
        # GET <controller_url>/controller/alerting/rest/v1/applications/<application_id>/health-rules/{health-rule-id}
        self.set_request_logging()
        self.do_verbose_print('Doing health rule get...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        if self.args.name is None and self.args.id is None:
            print('No health rule name specified with --name or id with --id, see --help')
            sys.exit()
        if self.args.id is None:
            self.do_verbose_print('health rule name given, getting list to get id')
            self.args.id = self._get_rule_id(self.args.name)
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        url = f'controller/alerting/rest/v1/applications/{self.args.application}/health-rules/{self.args.id}'
        headers, auth = self.set_auth_headers()
        try:
            #response = requests.get(url, headers=headers)
            response = requests.get(base_url+url, auth=auth, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'Health Rule api export call returned HTTPError: {err}')
        rule_data = response.json()
        self.do_verbose_print(json.dumps(rule_data)[0:200] + '...')
        json_obj = json.dumps(rule_data)
        if self.args.output:
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return rule_data