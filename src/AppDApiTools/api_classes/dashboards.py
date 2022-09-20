import base64
import copy
import difflib
import json
import os.path
import re
import sys
import zipfile
from datetime import datetime
from functools import reduce
from cryptography.fernet import Fernet
import requests
import logging
from .api_base import ApiBase


class Dashboards(ApiBase):
    builder_config = {"search": [], "replace": []}

    @classmethod
    def get_function_parms(cls, subparser):
        # print('getFunctions')
        functions = [
            'export',
            'import',
            'duplicate',
            'backup',
            'multi_dupe',
            # 'convert_absolute',
        ]
        class_commands = subparser.add_parser('Dashboards', help='Dashboards commands')
        class_commands.add_argument('function', choices=functions, help='The Dashboards api function to run')
        class_commands.add_argument('--id', help='Specific dashboard id or comma list')
        class_commands.add_argument('--builder_config', help='Search and replace config file in json')
        class_commands.add_argument('--input', help='The input template created with the AppDynamics UI')
        class_commands.add_argument('--output', help='The output file.', nargs='?', const='dashboard_name')
        class_commands.add_argument('--auth', help='The auth scheme.', choices=['key', 'user'], default='key')
        class_commands.add_argument('--prettify', help='Prettify the json output', action='store_true')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--name', help='Set the name of the new dashboard', default=False)
        return class_commands

    @classmethod
    def run(cls, args, config):

        dash = Dashboards(config, args)
        if args.function == 'export':
            dash.do_export()
        if args.function == 'import':
            dash.do_import()
        if args.function == 'duplicate':
            dash.duplicate()
        if args.function == 'backup':
            dash.backup()
        if args.function == 'multi_dupe':
            dash.multi_dupe()

    def __init__(self, config, args):
        super().__init__(config, args)

    def multi_dupe(self):
        config_list = []
        self.do_verbose_print('Doing Multiple Dashboard Duplicate...')
        if self.args.builder_config is None:
            print('No builder config specified with --builder_config, see --help')
            sys.exit()
        self.do_verbose_print(self.args.builder_config)
        if ',' in self.args.builder_config:
            self.do_verbose_print(f'We have a comma delimited file list: {self.args.builder_config}')
            config_list = self.args.builder_config.split(',')

        if os.path.isdir(self.args.builder_config):
            self.do_verbose_print(f'We have a folder with json configs: {self.args.builder_config}')
            for file in os.listdir(self.args.builder_config):
                if file.endswith(".json"):
                    config_list.append(os.path.join(self.args.builder_config, file))
        self.do_verbose_print(config_list)
        multi_output = False
        multi_dir = None
        if self.args.output is not None and self.args.output != 'dashboard_name':
            # for multi if we have output, we need a dir
            if os.path.isdir(self.args.output):
                multi_dir = self.args.output
                multi_output = True
        conf_counter = 1
        for config in config_list:
            # input is 1 to many so leave --id and --input parms as is
            self.args.builder_config = config
            self._get_builder_config()
            self.args.output = None
            if multi_output:
                self.args.output = os.path.join(multi_dir, self._get_option("setNewName", str(conf_counter))+".json")
            self.duplicate()

        return

    def do_import(self, dashboard=None):
        self.set_request_logging()
        self.do_verbose_print('Doing dashboard Import...')
        dash_file_name = 'dashboard.json'
        if dashboard is None and self.args.input is None:
            print('No dashboard data or specified input file with --input, see --help')
            sys.exit()
        if dashboard is None:
            self.do_verbose_print(f'Loading dashboard input from {self.args.input}')
            dashboard = json.loads(open(self.args.input, "r").read())
            dash_file_name = os.path.basename(self.args.input)
        dashboard = {'file': (dash_file_name, json.dumps(dashboard))}
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
        base_url = self.config['CONTROLLER_INFO']['base_url']
        url = base_url + 'controller/CustomDashboardImportExportServlet?output=JSON'
        try:
            response = requests.post(url, auth=auth, files=dashboard, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'Dashboard api export call returned HTTPError: {err}')
        dash_data = response.json()
        self.do_verbose_print(json.dumps(dash_data)[0:200]+'...')
        return dash_data

    def do_export(self):

        self.set_request_logging()
        self.do_verbose_print('Doing dashboard Export...')
        if self.args.id is None:
            print('No dashboard id specified with --id, see --help')
            sys.exit()
        self.do_verbose_print(f'Attempting to export dashboard with id={self.args.id}')
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
        base_url = self.config['CONTROLLER_INFO']['base_url']
        url = base_url + 'controller/CustomDashboardImportExportServlet?dashboardId=' + self.args.id + '&output=JSON'
        try:
            #response = requests.get(url, headers=headers)
            response = requests.get(url, auth=auth, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(f'Dashboard api export call returned HTTPError: {err}')
        dash_data = response.json()
        self.do_verbose_print(json.dumps(dash_data)[0:200] + '...')
        try:
            d_file = dash_data['name'].strip() + ".json"
        except KeyError as err:
            raise SystemExit(f'Dashboard element: {err} not found, likely invalid dashboard id')
        json_obj = json.dumps(dash_data)
        if self.args.output:
            if self.args.output != 'dashboard_name':
                self.do_verbose_print(f'Setting output name from commandline instead of dashboard name...')
                d_file = self.args.output
            with open(d_file, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {d_file}')
                outfile.write(json_obj)

        return dash_data

    # Process the options. If an option is not set, return the default value
    def _get_option(self, option, default):
        if "options" not in self.builder_config:
            return default
        if option not in self.builder_config["options"]:
            return default
        return self.builder_config["options"][option]

    def _set_option(self, option, value):
        if "options" not in self.builder_config:
            self.builder_config["options"] = {option: value}
            return self.builder_config["options"][option]

        self.builder_config["options"][option] = value
        return self.builder_config["options"][option]

    def _get_builder_config(self) -> None:
        if self.args.builder_config:
            self.builder_config = json.loads(open(self.args.builder_config, "r").read())
            return None
        self.do_verbose_print('Using empty builder config since none specified, see --help')
        return None

    def _normalize_pattern(self, pattern):
        if isinstance(pattern, list):
            for i in range(len(pattern)):
                pattern[i] = self._normalize_pattern(pattern[i])
            return pattern

        if not isinstance(pattern, dict):
            return {"value": pattern, "regex": False}

        if "regex" not in pattern:
            pattern["regex"] = False

        if "func" in pattern and pattern["func"] == "base64image":
            pattern["value"] = "data:image/png;base64," + str(base64.b64encode(open(pattern["value"], "rb").read()))

        return pattern

    # Calculate the dimensions of a AppDynamics dashboard
    def _calculate_dimensions(self, dashboard):
        max_x = 0  # height
        max_y = 0  # width
        min_x = dashboard["width"]
        min_y = dashboard["height"]

        # Compute the dimension of the current dashboard
        for widget in dashboard["widgetTemplates"]:
            max_y = widget["y"] + widget["height"] if widget["y"] + widget["height"] > max_y else max_y
            min_x = widget["x"] if widget["x"] < min_x else min_x
            min_y = widget["y"] if widget["y"] < min_y else min_y
            max_x = widget["x"] + widget["width"] if widget["x"] + widget["width"] > max_x else max_x

        return max_x, max_y, min_x, min_y

    # The following function is the "main" method processing a dashboard search/replace
    def _repeat_dashboard(self, dashboard):
        # Should the existing dashboard be replaced or should we extend the list?
        extend_widgets = self._get_option("extendWidgets", True)
        set_new_name = self._get_option("setNewName", None)
        top_offset = self._get_option("topOffset", 0)
        left_offset = self._get_option("leftOffset", 0)
        max_x, max_y, min_x, min_y = self._calculate_dimensions(dashboard)

        new_widgets = []
        i = 1 if extend_widgets else 0
        search = self._normalize_pattern(self.builder_config["search"])
        # Walk over all search&replace patterns and create a new "row" for each of them.
        for replace in self._normalize_pattern(self.builder_config["replace"]):
            y_offset = i * max_y + top_offset
            if (i + 1) * max_y + top_offset > dashboard["height"]:
                dashboard["height"] = (i + 1) * max_y + top_offset
            if reduce(lambda carry, element: carry and isinstance(element, list), replace, True):
                j = 0
                for column in replace:
                    x_offset = j * max_x + left_offset
                    if (j + 1) * max_y + left_offset > dashboard["width"]:
                        dashboard["width"] = (j + 1) * max_y + left_offset
                    for widget in dashboard["widgetTemplates"]:
                        c = self._walk(copy.deepcopy(widget), search, column)
                        c["y"] += y_offset
                        c["x"] += x_offset
                        new_widgets.append(c)
                    j += 1
            else:
                for widget in dashboard["widgetTemplates"]:
                    c = self._walk(copy.deepcopy(widget), search, replace)
                    c["y"] += y_offset
                    new_widgets.append(c)
            i += 1

        if extend_widgets:
            dashboard["widgetTemplates"].extend(new_widgets)
        else:
            dashboard["widgetTemplates"] = new_widgets

        if set_new_name is not None:
            dashboard["name"] = set_new_name

        return dashboard

    def _walk(self, widget, search, replace):
        for key in widget if isinstance(widget, dict) else range(len(widget)):
            widget[key] = self._process_widget_property(widget[key], key, search, replace)

        return widget

    # Process a single property of a widget
    def _process_widget_property(self, prop, key, search, replace):
        # Walk recursively if the property is a list or dict
        if isinstance(prop, (dict, list)):
            return self._walk(prop, search, replace)

        old = prop
        for i in range(len(search)):
            prop = self._search_and_replace(search[i], key, replace[i], prop)

        if old != prop:
            self.do_verbose_print(f'Modifying Property: {self._show_diff(old, prop)}')

        return prop

    # Source: http://stackoverflow.com/questions/774316/python-difflib-highlighting-differences-inline
    def _show_diff(self, old, new) -> str:
        seqm = difflib.SequenceMatcher(None, str(old), str(new))
        """Unify operations between two compared strings
    seqm is a difflib.SequenceMatcher instance whose a & b are strings"""
        output = []
        for opcode, a0, a1, b0, b1 in seqm.get_opcodes():
            if opcode == 'equal':
                output.append(seqm.a[a0:a1])
            else:
                output.append("\033[91m" + seqm.b[b0:b1] + "\033[00m")
        return ''.join(output)

    # Apply search and replace patterns onto a value
    def _search_and_replace(self, search, key, replace, target):
        if "key" in search and search["key"] != key:
            return target

        if "regex" in search and search["regex"]:
            return re.sub(re.compile(search["value"]), replace["value"], target)

        if hasattr(target, "replace"):
            return target.replace(str(search["value"]), str(replace["value"]))

        # if isinstance(target, (int,long)):
        if isinstance(target, (int, int)):
            return replace["value"] if target == search["value"] else target

    def backup(self):
        self.do_verbose_print(f'Doing dashboard Backup...')
        if self.args.id is None:
            print('backup function needs --id with value[s] see --help')
            sys.exit()
        if self.args.output is None or self.args.output == 'dashboard_name':
            self.args.output = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")+'.zip'
            self.do_verbose_print(f'Using generated zip filename: {self.args.output}')
        self.do_verbose_print(self.args.id)
        # get and split the args cause we will override id in loop
        dashboard_list = self.args.id.split(',')
        # get and null output for export loop
        zip_output = self.args.output
        self.args.output = None
        self.do_verbose_print(dashboard_list)
        with zipfile.ZipFile(zip_output, mode="w") as backup:
            for dashboard in dashboard_list:
                # reset id for call below
                self.args.id = dashboard
                dashboard_data = self.do_export()
                dashboard_name = dashboard_data["name"]+".json"
                backup.writestr(dashboard_name, json.dumps(dashboard_data))

    def duplicate(self):
        self.do_verbose_print('Doing dashboard Duplication...')
        self._get_builder_config()
        # we are wrapping builder with specific functions so lets guide config as such
        extend_widgets = self._get_option("extendWidgets", False)
        if extend_widgets:
            warning = """You have specified to duplicate a dashboard with search and replace, 
            but configuration is set to extend dashboard elements"""
            answer = input('Do you want to change it? [yes|no]')
            if 'yes' in answer.lower():
                self._set_option("extendWidgets", False)
        source_dash = None
        if self.args.input:
            self.do_verbose_print('--input specified so using that, see --help')
            source_dash = json.loads(open(self.args.input, "r").read())
        else:
            self.do_verbose_print('--id specified so calling export, see --help')
            source_dash = self.do_export()
        if source_dash is None:
            print('--id or --input was not specified so exiting, see --help')
            sys.exit()
        result_dash = self._repeat_dashboard(source_dash)
        if self.args.name:
            self.do_verbose_print(f'--name specified so setting new dashboard name to {self.args.name}...')
            result_dash["name"] = self.args.name
        result = json.dumps(result_dash, sort_keys=self.args.prettify, indent=4 if self.args.prettify else None)

        if self.args.output is not None:
            try:
                d_file = result_dash['name'].strip() + ".json"
            except KeyError as err:
                raise SystemExit(f'Dashboard element: {err} not found, likely invalid dashboard id')
            if self.args.output != 'dashboard_name':
                self.do_verbose_print(f'Setting output name from commandline instead of dashboard name...')
                d_file = self.args.output
            self.do_verbose_print(f'--output specified so writing new dashboard name to {d_file}...')
            with open(d_file, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {d_file}')
                outfile.write(result)
        else:
            self.do_import(result_dash)
