import datetime
import json
import sys

from cryptography.fernet import Fernet
import requests
import logging
import argparse
from .api_base import ApiBase
from .applications import Applications


class Healthrules(ApiBase):
# TODO Action list of all apps add that
    @classmethod
    def get_function_parms(cls, subparser):
        # print('getFunctions')
        functions = [
            'list',
            'get',
            'create',
            'delete',
            'suppression_list',
            'suppression_get',
            'suppression_create',
            'search',
            'sync_rule'
        ]
        class_commands = subparser.add_parser('Healthrules', help='Healthrules commands')
        class_commands.add_argument('function', choices=functions, help='The Healthrules api function to run')
        class_commands.add_argument('--application', help='Specific Applications id or name')
        class_commands.add_argument('--system', help='Specific system prefix config to use')
        class_commands.add_argument('--input', help='The input template created with the AppDynamics UI')
        class_commands.add_argument('--output', help='The output file.', nargs='?', const='dashboard_name')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--name', help='Health Rule name or Suppression name')
        class_commands.add_argument('--id', help='Health Rule id or Suppression id')
        class_commands.add_argument('--start', help='Suppression start time 24HR format (YYYY-MM-DD HH:MM:SS)')
        class_commands.add_argument('--duration', help='Suppression duration in minutes')
        class_commands.add_argument('--rule_list', help='Suppression rule names as quoted comma delimited list')
        class_commands.add_argument('--auth', help='The auth scheme.', choices=['key', 'user'], default='key')
        class_commands.add_argument('--timezone', help='Suppression rule timezone string')
        return class_commands

    @classmethod
    def run(cls, args, config):
        app = Healthrules(config, args)
        app.set_config_prefixes()
        if args.function == 'list':
            app.get_health_list()
        if args.function == 'get':
            app.get_rule()
        if args.function == 'create':
            app.create_rule()
        if args.function == 'delete':
            app.delete_rule()
        if args.function == 'sync_rule':
            app.sync_health_rule()
        if args.function == 'suppression_list':
            app.get_action_suppression_list()
        if args.function == 'suppression_get':
            app.get_action_suppression()
        if args.function == 'suppression_create':
            app.create_action_suppression()
        if args.function == 'search':
            app.search()

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

    def _get_app_action_list(self, ids=None, names=None):
        output_tmp = self.args.output
        self.args.output = None
        alist = self.get_action_suppression_list()
        self.do_verbose_print(f'Get Suppression id {alist}')
        self.args.output = output_tmp
        # TODO this below still doesn't work right with multiple apps
        filtered_list = []
        id_list = []
        if ids is not None:
            id_list = ids.split(',')
        name_list = []
        if names is not None:
            name_list = names.split(',')
        #print(id_list)
        #print(name_list)
        for app in alist:
            #print(app)
            filtered_actions = []
            for action_suppression in app['action_suppressions']:
                for id in id_list:
                    if id == action_suppression['id']:
                        filtered_actions.append(action_suppression)
                for name in name_list:
                    if name == action_suppression['name']:
                        filtered_actions.append(action_suppression)
            if len(filtered_actions) > 0:
                app_copy = app
                app_copy['action_suppressions'] = filtered_actions
                filtered_list.append(app_copy)
        return filtered_list

    def sync_health_rule(self):
        self.set_request_logging()
        self.do_verbose_print('Doing Health Rule Sync...')
        if self.args.input is None:
            print('No json health rule input specified --input, see --help')
            sys.exit()
        if self.args.application is None:
            self.do_verbose_print('No applications specified, assuming all')
            self.args.application = 'all'
        health_rule = json.loads(open(self.args.input, "r").read())
        self.args.name = health_rule["name"]
        self.do_verbose_print(f'Searching for rules named: {self.args.name}')
        output_temp = self.args.output
        self.args.output = None
        health_list = self.search()
        self.do_verbose_print(f'The search list of all apps: {health_list}')
        created_list = []
        for app in health_list:
            # for sync we depend on search of all apps giving us empty rule list when name not found
            if len(app['health_rules']) > 0:
                continue
            # we will run create, output arg is set to none already, input arg is used and we just reset the all apps arg
            created_list.append(self.create_rule(app_data=[app]))
        self.args.output = output_temp
        if self.args.output:
            json_obj = json.dumps(created_list)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return created_list

    def delete_rule(self, app_data=None):
        self.set_request_logging()
        self.do_verbose_print('Doing Health Rule Delete...')
        if self.args.application is None and app_data is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        if app_data is None:
            app_data = self._get_app_data()
        if self.args.name is None and self.args.id is None:
            print('No health rule name specified with --name or id with --id, see --help')
            sys.exit()
        rids = []
        if self.args.id is None:
            self.do_verbose_print('health rule name given, getting list to get id')
            rids = self._get_rule_id_with_app(rule_name=self.args.name)
        else:
            rids = self._get_rule_id_with_app(rule_id=self.args.id)
        self.do_verbose_print(f'rule ids by app: {rids}')
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        # DELETE <controller_url>/controller/alerting/rest/v1/applications/<application_id>/health-rules/{health-rule-id}

        for app in app_data:
            if app["id"] not in rids or rids[app["id"]]["id"] is None:
                continue
            url = f'controller/alerting/rest/v1/applications/{app["id"]}/health-rules/{rids[app["id"]]["id"]}'

            try:
                # response = requests.get(url, headers=headers)
                response = requests.delete(base_url + url, auth=auth, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Health Rule Delete api export call returned HTTPError: {err}')
            self.do_verbose_print(f'Health Rule: {rids[app["id"]]["id"]} deleted!')


    def create_rule(self, app_data=None):
        self.set_request_logging()
        self.do_verbose_print('Doing Health Rule Create...')
        if self.args.application is None and app_data is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        if self.args.input is None:
            print('No json health rule input specified --input, see --help')
            sys.exit()
        if app_data is None:
            app_data = self._get_app_data()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        health_rule = json.loads(open(self.args.input, "r").read())
        # POST <controller_url>/controller/alerting/rest/v1/applications/<application_id>/health-rules
        health_rule_data = []
        for app in app_data:
            url = f'controller/alerting/rest/v1/applications/{app["id"]}/health-rules'

            try:
                # response = requests.get(url, headers=headers)
                response = requests.post(base_url + url, auth=auth, headers=headers, json=health_rule)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Health Rule create call returned HTTPError: {err}')
            app_copy = app
            app_copy['health_rule_details'] = [response.json()]
            health_rule_data.append(app_copy)
            self.do_verbose_print(json.dumps(app_copy)[0:200] + '...')
        if self.args.output:
            json_obj = json.dumps(health_rule_data)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return health_rule_data

    def search(self):
        self.set_request_logging()
        self.do_verbose_print('Doing Health Rule Search...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        if self.args.name is None:
            print('No health rule name specified with --name, see --help')
            sys.exit()
        output_tmp = self.args.output
        self.args.output = None
        health_list = self.get_health_list()
        self.args.output = output_tmp
        # simplicity of getting done lets just loop and remove from whole list

        for app in health_list:
            match_rule_list = []
            for rule in app["health_rules"]:
                if self.args.name.lower() in rule['name'].lower():
                    match_rule_list.append(rule)
            app["health_rules"] = match_rule_list

        if self.args.output:
            json_obj = json.dumps(health_list)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return health_list

    def create_action_suppression(self):
        # TODO database action suppressions - no api for databases
        # POST <controller_url>/controller/alerting/rest/v1/applications/<application_id>/action-suppressions
        self.set_request_logging()
        self.do_verbose_print('Doing Action Suppression List...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        app_data = self._get_app_data()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        action_suppression = {}
        if self.args.input is not None:
            # just load json input and post
            action_suppression = json.loads(open(self.args.input, "r").read())
        else:
            if self.args.name is None:
                print('No --input so --name is required, see --help')
                sys.exit()
            if self.args.start is None:
                print('No --input so --start is required, see --help')
                sys.exit()
            if self.args.duration is None:
                print('No --input so --duration is required, see --help')
                sys.exit()
            if self.args.rule_list is None:
                print('No --input so --rule_list is required, see --help')
                sys.exit()
            if self.args.timezone is None:
                print('No --timezone so -which is required, see --help')
                sys.exit()
            start = datetime.datetime.strptime(self.args.start, '%Y-%m-%d %H:%M:%S')
            end = start + datetime.timedelta(minutes=int(self.args.duration))
            rule_list = self.args.rule_list.split(',')
            action_suppression['name'] = self.args.name
            action_suppression["disableAgentReporting"] = False
            action_suppression["recurringSchedule"] = None
            action_suppression["suppressionScheduleType"] = "ONE_TIME"
            action_suppression["timezone"] = self.args.timezone
            action_suppression["startTime"] = start.strftime('%Y-%m-%dT%H:%M:%S')
            action_suppression["endTime"] = end.strftime('%Y-%m-%dT%H:%M:%S')
            action_suppression["affects"] = {"affectedInfoType": "APPLICATION"}
            action_suppression["healthRuleScope"] = {"healthRuleScopeType": "SPECIFIC_HEALTH_RULES", "healthRules": rule_list}

            self.do_verbose_print(f'Built suppresion create json: {action_suppression}')
        headers, auth = self.set_auth_headers()
        action_suppression_data = []
        for app in app_data:
            url = f'controller/alerting/rest/v1/applications/{app["id"]}/action-suppressions'

            try:
                # response = requests.get(url, headers=headers)
                response = requests.post(base_url + url, auth=auth, headers=headers, json=action_suppression)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Action Suppression create call returned HTTPError: {err}')
            app_copy = app
            app_copy['action_suppressions'] = [response.json()]
            action_suppression_data.append(app_copy)
            self.do_verbose_print(json.dumps(app_copy)[0:200] + '...')

        if self.args.output:
            json_obj = json.dumps(action_suppression_data)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return action_suppression_data

    def get_action_suppression(self):
        # GET <controller_url>/controller/alerting/rest/v1/applications/<application_id>/action-suppressions/{action-suppression-id}
        self.set_request_logging()
        self.do_verbose_print('Doing Action Suppression List...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        #app_data = self._get_app_data()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        if self.args.name is None and self.args.id is None:
            print('No action suppression name specified with --name or id with --id, see --help')
            sys.exit()
        app_data = self._get_app_action_list(self.args.id, self.args.name)
        headers, auth = self.set_auth_headers()
        action_suppression_data = []
        self.do_verbose_print(app_data)
        for app in app_data:
            app_actions = []
            for action in app['action_suppressions']:
                url = f'controller/alerting/rest/v1/applications/{app["id"]}/action-suppressions/{action["id"]}?output=JSON'

                try:
                    # response = requests.get(url, headers=headers)
                    response = requests.get(base_url + url, auth=auth, headers=headers)
                    response.raise_for_status()
                except requests.exceptions.HTTPError as err:
                    raise SystemExit(f'Action Suppression details call returned HTTPError: {err}')

                self.do_verbose_print(json.dumps(response.json())[0:200] + '...')
                app_actions.append(response.json())
            app_copy = app
            app_copy['action_suppressions'] = app_actions
            action_suppression_data.append(app_copy)

        if self.args.output:
            json_obj = json.dumps(action_suppression_data)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return action_suppression_data

    def get_action_suppression_list(self):
        # GET <controller_url>/controller/alerting/rest/v1/applications/<application_id>/action-suppressions
        self.set_request_logging()
        self.do_verbose_print('Doing Action Suppression List...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        app_data = self._get_app_data()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        action_suppression_data = []
        for app in app_data:
            url = f'controller/alerting/rest/v1/applications/{app["id"]}/action-suppressions?output=JSON'
            try:
                # response = requests.get(url, headers=headers)
                response = requests.get(base_url + url, auth=auth, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Action Suppression list call returned HTTPError: {err}')
            self.do_verbose_print(json.dumps(response.json())[0:200] + '...')
            app['action_suppressions'] = response.json()
            action_suppression_data.append(app)

        if self.args.output:
            json_obj = json.dumps(action_suppression_data)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return action_suppression_data

    def get_health_list(self, app_data=None):
        # GET <controller_url>/controller/alerting/rest/v1/applications/<application_id>/health-rules
        self.set_request_logging()
        self.do_verbose_print('Doing health rule List...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        if app_data is None:
            app_data = self._get_app_data()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        rule_data = []
        for app in app_data:
            url = f'controller/alerting/rest/v1/applications/{app["id"]}/health-rules?output=JSON'

            try:
                #response = requests.get(url, headers=headers)
                response = requests.get(base_url+url, auth=auth, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Health Rule api export call returned HTTPError: {err}')
            app['health_rules'] = response.json()
            rule_data.append(app)
            self.do_verbose_print(json.dumps(response.json())[0:200] + '...')
        json_obj = json.dumps(rule_data)
        if self.args.output:
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return rule_data

    def _get_rule_id_with_app(self, rule_name=None, rule_id=None):
        output_tmp = self.args.output
        self.args.output = None
        rule_list = self.get_health_list()
        self.args.output = output_tmp
        rule_ids = {}
        if rule_id is not None:
            rule_id = int(rule_id)
        for app in rule_list:
            for rule in app['health_rules']:
                # self.do_verbose_print(f'Searching for rule id: {rule_id}, rule_name: {rule_name} in {rule}')
                if rule_name == rule["name"] or rule_id == rule['id']:
                    # self.do_verbose_print(f'Found for rule id: {rule_id}, rule_name: {rule_name} in {rule}')
                    rule_ids[app['id']] = {'id': rule['id']}
        return rule_ids

    def get_rule(self):
        # GET <controller_url>/controller/alerting/rest/v1/applications/<application_id>/health-rules/{health-rule-id}
        self.set_request_logging()
        self.do_verbose_print('Doing health rule get...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        app_data = self._get_app_data()
        self.do_verbose_print("Got App Data")
        self.do_verbose_print(app_data)
        if self.args.name is None and self.args.id is None:
            print('No health rule name specified with --name or id with --id, see --help')
            sys.exit()
        rids = []
        if self.args.id is None:
            self.do_verbose_print('health rule name given, getting list to get id')
            rids = self._get_rule_id_with_app(rule_name=self.args.name)
        else:
            rids = self._get_rule_id_with_app(rule_id=self.args.id)
        self.do_verbose_print(f'rule ids by app: {rids}')
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        rule_data = []
        for app in app_data:
            if app["id"] not in rids or rids[app["id"]]["id"] is None:
                continue
            url = f'controller/alerting/rest/v1/applications/{app["id"]}/health-rules/{rids[app["id"]]["id"]}'

            try:
                #response = requests.get(url, headers=headers)
                response = requests.get(base_url+url, auth=auth, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Health Rule api export call returned HTTPError: {err}')
            app['health_rule_detail'] = response.json()
            rule_data.append(app)
            self.do_verbose_print(json.dumps(response.json())[0:200] + '...')

        if self.args.output:
            json_obj = json.dumps(rule_data)
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return rule_data
