import base64
import copy
import difflib
import json
import os.path
import re
import sys
from functools import reduce

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
            'replicate',
            'tile',
            'convert_absolute',
        ]
        class_commands = subparser.add_parser('Dashboards', help='Dashboards commands')
        class_commands.add_argument('function', choices=functions, help='The Dashboards api function to run')
        class_commands.add_argument('--id', help='Specific dashboard id')
        class_commands.add_argument('--builder_config', help='Search and replace config file in json')
        class_commands.add_argument('--input', help='The input template created with the AppDynamics UI')
        class_commands.add_argument('--output', help='The output file.')
        class_commands.add_argument('--prettify', help='Prettify the json output', action='store_true')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--name', help='Set the name of the new dashboard', default=False)
        return class_commands

    @classmethod
    def run(cls, args, config):

        # TODO replicate a dashboard with search and replace as a whole
        dash = Dashboards(config, args)
        if args.function == 'export':
            dash.do_export()
        if args.function == 'import':
            dash.do_import()
        if args.function == 'duplicate':
            dash.duplicate()

    def __init__(self, config, args):
        super().__init__(config, args)

    def __set_request_logging(self):
        if self.args.verbose:
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True

    def _do_verbose_print(self, msg):
        if self.args.verbose:
            print(msg)

    def do_import(self, dashboard=None):
        self.__set_request_logging()
        self._do_verbose_print('Doing dashboard Import...')
        dash_file_name = 'dashboard.json'
        if dashboard is None and self.args.input is None:
            print('No dashboard data or specified input file with --input, see --help')
            sys.exit()
        if dashboard is None:
            self._do_verbose_print(f'Loading dashboard input from {self.args.input}')
            dashboard = json.loads(open(self.args.input, "r").read())
            dash_file_name = os.path.basename(self.args.input)
        dashboard = {'file': (dash_file_name, json.dumps(dashboard))}
        print(dashboard)
        print(type(dashboard))
        token = self.get_oauth_token()
        base_url = self.config['CONTROLLER_INFO']['base_url']
        #headers = {"Authorization": "Bearer " + token}
        auth = (self.config['CONTROLLER_INFO']['user']+'@'+self.config['CONTROLLER_INFO']['account_name'], self.config['CONTROLLER_INFO']['psw'])
        url = base_url + 'controller/CustomDashboardImportExportServlet?output=JSON'
        response = requests.post(url, auth=auth, files=dashboard)
        dash_data = response.json()
        self._do_verbose_print(dash_data)
        self._do_verbose_print(response.text)

    def do_export(self):
        self.__set_request_logging()
        self._do_verbose_print('Doing dashboard Export...')
        if self.args.id is None:
            print('No dashboard id specified with --id, see --help')
            sys.exit()
        self._do_verbose_print(f'Attempting to export dashboard with id={self.args.id}')
        token = self.get_oauth_token()
        base_url = self.config['CONTROLLER_INFO']['base_url']
        headers = {"Authorization": "Bearer " + token}
        url = base_url + 'controller/CustomDashboardImportExportServlet?dashboardId=' + self.args.id + '&output=JSON'
        response = requests.get(url, headers=headers)
        dash_data = response.json()
        d_file = dash_data['name'].strip() + ".json"
        if self.args.output:
            d_file = self.args.output
        json_obj = json.dumps(dash_data)
        with open(d_file, "w") as outfile:
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
        self._do_verbose_print('Using empty builder config since none specified, see --help')
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
            self._do_verbose_print(self._show_diff(old, prop))

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

    def duplicate(self):
        self._do_verbose_print('Doing dashboard Duplication...')
        self._get_builder_config()
        # we are wrapping builder with specific functions so lets guide config as such
        extend_widgets = self._get_option("extendWidgets", False)
        if extend_widgets:
            warning = """You have specified to duplicate a dashboard with search and replace, 
            but configuration is set to extend dashboard elements"""
            print(warning)
            answer = input('Do you want to change it? [yes|no]')
            if 'yes' in answer.lower():
                self._set_option("extendWidgets", False)
        source_dash = None
        if self.args.input:
            self._do_verbose_print('--input specified so using that, see --help')
            source_dash = json.loads(open(self.args.input, "r").read())
        else:
            self._do_verbose_print('--id specified so calling export, see --help')
            source_dash = self.do_export()
        if source_dash is None:
            self._do_verbose_print('--id or --input was not specified so exiting, see --help')
            return
        result_dash = self._repeat_dashboard(source_dash)
        if self.args.name:
            self._do_verbose_print(f'--name specified so setting new dashboard name to {self.args.name}...')
            result_dash["name"] = self.args.name
        result = json.dumps(result_dash, sort_keys=self.args.prettify, indent=4 if self.args.prettify else None)

        if self.args.output:
            self._do_verbose_print(f'--output specified so writing new dashboard name to {self.args.output}...')
            new_file = open(self.args.output, "w")
            new_file.write(result)
        else:
            print(result)
