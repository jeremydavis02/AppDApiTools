import datetime
import json
import sys

from cryptography.fernet import Fernet
import requests
import logging
import argparse
from .api_base import ApiBase
from .applications import Applications


class Users(ApiBase):

    @classmethod
    def get_function_parms(cls, subparser):
        # print('getFunctions')
        functions = [
            'list',
            'get',
            'all_data',
            'get_role'
        ]
        class_commands = subparser.add_parser('Users', help='User commands')
        class_commands.add_argument('function', choices=functions, help='The Metrics api function to run')
        class_commands.add_argument('--application', help='Specific Applications id or name')
        class_commands.add_argument('--system', help='Specific system prefix config to use')
        class_commands.add_argument('--input', help='The input template created with the AppDynamics UI')
        class_commands.add_argument('--output', help='The output file.', nargs='?', const='dashboard_name')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--name', help='Health Rule name or Suppression name')
        class_commands.add_argument('--id', help='Health Rule id or Suppression id')
        class_commands.add_argument('--auth', help='The auth scheme.', choices=['key', 'user'], default='key')
        return class_commands

    @classmethod
    def run(cls, args, config):
        app = Users(config, args)
        app.set_config_prefixes()
        if args.function == 'list':
            app.list()
        if args.function == 'get':
            app.get()
        if args.function == 'all_data':
            app.all_data()
        if args.function == 'get_role':
            app.get_role()

    def get_role(self, **kwargs):
        self.set_request_logging()
        self.do_verbose_print('Doing Role Get...')
        # GET /controller/api/rbac/v1/roles/[roleId]?include-permissions=true
        # GET /controller/api/rbac/v1/roles/name/[RoleName]?include-permissions=true
        # TODO below with kwargs overrides is cleaner way to override config parser for internal calls so replace other code with this
        role_name = self.args.name
        role_id = self.args.id
        role_output = self.args.output
        if 'name' in kwargs:
            role_name = kwargs['name']
        if 'id' in kwargs:
            role_id = kwargs['id']
        if 'output' in kwargs:
            role_output = kwargs['output']
        if role_name is None and role_id is None:
            print('No role specified with --name or --id, see --help')
            sys.exit()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        url = f'controller/api/rbac/v1/roles/name/{role_name}?include-permissions=true'
        if role_id is not None:
            # id will take precedence over name if both given
            url = f'controller/api/rbac/v1/roles/{role_id}?include-permissions=true'
        try:
            response = requests.get(base_url + url, auth=auth, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'Health Rule api export call returned HTTPError: {err}')
        role_data = response.json()
        if role_output:
            json_obj = json.dumps(role_data)
            with open(role_output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return role_data

    def _get_role_ids(self, user_data):
        id_list = []
        self.do_verbose_print(f'Doing get role ids for: {user_data}')
        if 'roles' not in user_data:
            return id_list
        for r in user_data['roles']:
            id_list.append(r['id'])
        return id_list

    def all_data(self):
        self.set_request_logging()
        self.do_verbose_print('Doing Users list (all data)...')
        out_tmp = self.args.output
        list = self.list()
        self.args.output = out_tmp
        all_data = {
            'users': [],
            'roles': []
        }
        role_id_set = set()
        for user in list["users"]:
            user = self.get(user_id=user["id"])
            all_data['users'].append(user)
            role_id_set.update(self._get_role_ids(user_data=user))
        for role_id in role_id_set:
            role = self.get_role(output=None, id=role_id)
            all_data['roles'].append(role)
        if self.args.output:
            json_obj = json.dumps(all_data)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return all_data

    def list(self):
        self.set_request_logging()
        self.do_verbose_print('Doing Users list...')


        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        users = None

        url = f'controller/api/rbac/v1/users?output=JSON'

        try:
            # response = requests.get(url, headers=headers)
            response = requests.get(base_url + url, auth=auth, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'User list api get call returned HTTPError: {err}')
        users = response.json()

        self.do_verbose_print(json.dumps(response.json())[0:200] + '...')
        if self.args.output:
            json_obj = json.dumps(users)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return users

    def get(self, user_id=None):
        self.set_request_logging()
        self.do_verbose_print('Doing Users Get...')
        if user_id is None and self.args.id is None:
            print('No user id specified with --id, see --help')
            sys.exit()
        if user_id is None:
            user_id = self.args.id
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        users = None

        url = f'controller/api/rbac/v1/users/{user_id}?output=JSON'

        try:
            # response = requests.get(url, headers=headers)
            response = requests.get(base_url + url, auth=auth, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'User get api get call returned HTTPError: {err}')
        users = response.json()

        self.do_verbose_print(json.dumps(response.json())[0:200] + '...')
        if self.args.output:
            json_obj = json.dumps(users)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return users

