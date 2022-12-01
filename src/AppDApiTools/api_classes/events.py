import datetime
import json
import sys

from cryptography.fernet import Fernet
import requests
import logging
import argparse
from .api_base import ApiBase
from .applications import Applications


class Events(ApiBase):

    @classmethod
    def get_function_parms(cls, subparser):
        # print('getFunctions')
        functions = [
            'create_schema',
            'get_schema',
            'delete_schema',
            'update_schema',
            'publish'
        ]
        class_commands = subparser.add_parser('Events', help='Events commands')
        class_commands.add_argument('function', choices=functions, help='The Events api function to run')
        class_commands.add_argument('--application', help='Specific Applications id or name')
        class_commands.add_argument('--system', help='Specific system prefix config to use')
        class_commands.add_argument('--input', help='The input schema json')
        class_commands.add_argument('--output', help='The output file.', nargs='?', const='dashboard_name')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--name', help='Event Schema name')
        class_commands.add_argument('--id', help='Health Rule id or Suppression id')
        class_commands.add_argument('--auth', help='The auth scheme.', choices=['key', 'user'], default='key')
        return class_commands

    @classmethod
    def run(cls, args, config):
        app = Events(config, args)
        app.set_config_prefixes()
        if args.function == 'create_schema':
            app.create_schema()
        if args.function == 'get_schema':
            app.get_schema()
        if args.function == 'delete_schema':
            app.delete_schema()
        if args.function == 'update_schema':
            app.update_schema()
        if args.function == 'publish':
            app.publish()

    # TODO add db event list function get - https://docs.appdynamics.com/appd/22.x/22.9/en/extend-appdynamics/appdynamics-apis/database-visibility-api#id-.DatabaseVisibilityAPIv22.1-GetallDatabaseAgentEvents
    # TODO GET /controller/rest/applications/_dbmon/events
    #todo server viz events too?

    def get_schema(self):
        self.set_request_logging()
        self.do_verbose_print('Doing Event Schema Get...')
        if self.args.name is None:
            print('No schema name specified --name, see --help')
            sys.exit()
        headers = {
            "X-Events-API-AccountName": self.config[self.CONTROLLER_SECTION]['global_account_name'],
            "X-Events-API-Key": self.config[self.CONTROLLER_SECTION]['events_api_key'],
            "Accept": 'application/vnd.appd.events+json;v=2',
            "Content-type": 'application/vnd.appd.events+json;v=2'
        }
        self.do_verbose_print(f'Headers set to: {headers}')
        url = f'{self.config[self.CONTROLLER_SECTION]["events_url"]}events/schema/{self.args.name}'

        try:
            # response = requests.get(url, headers=headers)
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'Custom Event Schema get call returned HTTPError: {err}')
        schema = response.json()
        json_obj = json.dumps(schema)
        if self.args.output:
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return schema

    def delete_schema(self):
        self.set_request_logging()
        self.do_verbose_print('Doing Event Schema Delete...')
        if self.args.name is None:
            print('No schema name specified --name, see --help')
            sys.exit()
        headers = {
            "X-Events-API-AccountName": self.config[self.CONTROLLER_SECTION]['global_account_name'],
            "X-Events-API-Key": self.config[self.CONTROLLER_SECTION]['events_api_key'],
            "Accept": 'application/vnd.appd.events+json;v=2'
        }
        self.do_verbose_print(f'Headers set to: {headers}')
        url = f'{self.config[self.CONTROLLER_SECTION]["events_url"]}events/schema/{self.args.name}'
        try:
            # response = requests.get(url, headers=headers)
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'Custom Event Schema create call returned HTTPError: {err}')

    def update_schema(self):
        self.set_request_logging()
        self.do_verbose_print('Doing Event Schema Update...')
        if self.args.name is None:
            print('No schema name specified --name, see --help')
            sys.exit()
        if self.args.input is None:
            print('No json schema input specified --input, see --help')
            sys.exit()
        headers = {
            "X-Events-API-AccountName": self.config[self.CONTROLLER_SECTION]['global_account_name'],
            "X-Events-API-Key": self.config[self.CONTROLLER_SECTION]['events_api_key'],
            "Accept": 'application/vnd.appd.events+json;v=2',
            "Content-type": 'application/vnd.appd.events+json;v=2'
        }
        self.do_verbose_print(f'Headers set to: {headers}')
        url = f'{self.config[self.CONTROLLER_SECTION]["events_url"]}events/schema/{self.args.name}'
        custom_schema = json.loads(open(self.args.input, "r").read())
        self.do_verbose_print(f'Custom Schema: {custom_schema}')
        try:
            # response = requests.get(url, headers=headers)
            response = requests.patch(url, headers=headers, json=custom_schema)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'Custom Event Schema create call returned HTTPError: {err}')

    def create_schema(self):
        self.set_request_logging()
        self.do_verbose_print('Doing Event Schema Create...')
        if self.args.name is None:
            print('No schema name specified --name, see --help')
            sys.exit()
        if self.args.input is None:
            print('No json schema input specified --input, see --help')
            sys.exit()
        headers = {
            "X-Events-API-AccountName": self.config[self.CONTROLLER_SECTION]['global_account_name'],
            "X-Events-API-Key": self.config[self.CONTROLLER_SECTION]['events_api_key'],
            "Accept": 'application/vnd.appd.events+json;v=2',
            "Content-type": 'application/vnd.appd.events+json;v=2'
        }
        self.do_verbose_print(f'Headers set to: {headers}')
        url = f'{self.config[self.CONTROLLER_SECTION]["events_url"]}events/schema/{self.args.name}'
        custom_schema = json.loads(open(self.args.input, "r").read())
        self.do_verbose_print(f'Custom Schema: {custom_schema}')
        try:
            # response = requests.get(url, headers=headers)
            response = requests.post(url, headers=headers, json=custom_schema)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'Custom Event Schema create call returned HTTPError: {err}')

    def publish(self):
        self.set_request_logging()
        self.do_verbose_print('Doing Event Publish...')
        if self.args.name is None:
            print('No schema name specified --name, see --help')
            sys.exit()
        if self.args.input is None:
            print('No json schema input specified --input, see --help')
            sys.exit()
        headers = {
            "X-Events-API-AccountName": self.config[self.CONTROLLER_SECTION]['global_account_name'],
            "X-Events-API-Key": self.config[self.CONTROLLER_SECTION]['events_api_key'],
            "Accept": 'application/vnd.appd.events+json;v=2',
            "Content-type": 'application/vnd.appd.events+json;v=2'
        }
        self.do_verbose_print(f'Headers set to: {headers}')
        url = f'{self.config[self.CONTROLLER_SECTION]["events_url"]}events/publish/{self.args.name}'
        event_data = json.loads(open(self.args.input, "r").read())
        self.do_verbose_print(f'Event Data: {event_data}')
        try:
            # response = requests.get(url, headers=headers)
            response = requests.post(url, headers=headers, json=event_data)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'Custom Event Schema create call returned HTTPError: {err}')
