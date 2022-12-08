import datetime
import json
import sys

from cryptography.fernet import Fernet
import requests
import logging
import argparse
from .api_base import ApiBase
from .applications import Applications


class Metrics(ApiBase):

    @classmethod
    def get_function_parms(cls, subparser):
        # print('getFunctions')
        functions = [
            'get_tree',
            'get_metric_data'
        ]
        class_commands = subparser.add_parser('Metrics', help='Metrics commands')
        class_commands.add_argument('function', choices=functions, help='The Metrics api function to run')
        class_commands.add_argument('--application', help='Specific Applications id or name')
        class_commands.add_argument('--system', help='Specific system prefix config to use')
        class_commands.add_argument('--input', help='The input template created with the AppDynamics UI')
        class_commands.add_argument('--output', help='The output file.')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--name', help='Metric name as full path')
        class_commands.add_argument('--id', help='Health Rule id or Suppression id')
        class_commands.add_argument('--rollup', help='Metric value rolled up or multiple values', default='true', choices=['true', 'false'])
        class_commands.add_argument('--start', help='Metric get start time 24HR format (YYYY-MM-DD HH:MM:SS)')
        class_commands.add_argument('--end', help='Metric get end time 24HR format (YYYY-MM-DD HH:MM:SS)')
        class_commands.add_argument('--auth', help='The auth scheme.', choices=['key', 'user'], default='key')

        return class_commands

    @classmethod
    def run(cls, args, config):
        app = Metrics(config, args)
        app.set_config_prefixes()
        if args.function == 'get_tree':
            app.get_tree()
        if args.function == 'get_metric_data':
            app.get_metric_data()

    def get_metric_data(self, **kwargs):
        self.set_request_logging()
        self.do_verbose_print('Doing Metric Hierarchy get...')
        application_name = self.args.application
        metric_path = self.args.name
        rollup = 'true'
        time_range_type = 'BETWEEN_TIMES'
        start_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        end_time = datetime.datetime.now()
        metric_output = self.args.output
        if 'application' in kwargs:
            application_name = kwargs['application']
        if 'name' in kwargs:
            metric_path = kwargs['name']
        if metric_path is None:
            print('No Metric name specified with --name, see --help')
            sys.exit()
        if self.args.rollup is not None:
            rollup = self.args.rollup
        if self.args.start is not None:
            start_time = datetime.datetime.strptime(self.args.start, '%Y-%m-%d %H:%M:%S')
        if 'start' in kwargs:
            start_time = datetime.datetime.strptime(kwargs['start'], '%Y-%m-%d %H:%M:%S')
        if self.args.end is not None:
            end_time = datetime.datetime.strptime(self.args.end, '%Y-%m-%d %H:%M:%S')
        if 'end' in kwargs:
            end_time = datetime.datetime.strptime(kwargs['end'], '%Y-%m-%d %H:%M:%S')
        if 'output' in kwargs:
            metric_output = kwargs['output']
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        metrics = None
        # Application Infrastructure Performance|Database  Agent|Custom Metrics|SQL|Metrics Uploaded
        # /controller/rest/applications/application_name/metric-data
        url = f'controller/rest/applications/{application_name}/metric-data?output=JSON'
        url = url + '&metric-path=' + metric_path
        url = url + '&rollup=' + rollup
        url = url + '&time-range-type=' + time_range_type
        url = url + '&start-time=' + str(self._get_epoch(start_time))
        url = url + '&end-time=' + str(self._get_epoch(end_time))

        try:
            # response = requests.get(url, headers=headers)
            response = requests.get(base_url + url, auth=auth, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'User get api get call returned HTTPError: {err}')
        metrics = response.json()

        self.do_verbose_print(json.dumps(response.json())[0:200] + '...')
        if metric_output:
            json_obj = json.dumps(metrics)
            with open(metric_output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {metric_output}')
                outfile.write(json_obj)
        return metrics

    def _get_epoch(self, date_time_obj):
        epoch = datetime.datetime.utcfromtimestamp(0)
        return int((date_time_obj - epoch).total_seconds() * 1000)

    def get_tree(self, app_data=None):
        self.set_request_logging()
        self.do_verbose_print('Doing Metric Hierarchy get...')
        if self.args.application is None and app_data is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        app_data = self._get_app_data()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        metric_data = []
        for app in app_data:
            url = f'controller/rest/applications/{app["id"]}/metrics?output=JSON'

            try:
                # response = requests.get(url, headers=headers)
                response = requests.get(base_url + url, auth=auth, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Metric Heirarchy api get call returned HTTPError: {err}')
            app['metric_hierarchy'] = response.json()
            metric_data.append(app)
            self.do_verbose_print(json.dumps(response.json())[0:200] + '...')
        if self.args.output:
            json_obj = json.dumps(metric_data)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return metric_data

    def _get_app_data(self):
        newargs = argparse.Namespace(subparser_name='Applications',
                                     function='get',
                                     id=None,
                                     name=None,
                                     verbose=self.args.verbose,
                                     auth=self.args.auth,
                                     output=None,
                                     system=self.args.system)
        app = Applications(self.config, newargs)
        app.set_config_prefixes()
        app.set_app_arg(self.args.application)
        app_data = app.get_app()
        return app_data
