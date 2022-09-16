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
        return class_commands

    @classmethod
    def run(cls, args, config):
        app = Applications(config, args)
        if args.function == 'list':
            app.get_app_list()

    def get_app_list(self):
        self.do_verbose_print('Doing dashboard Export...')
        # headers = {"Authorization": "Bearer "+token}
        # response = requests.get(base_url+'controller/rest/applications?output=JSON', headers=headers)
        # print(response.json())