import base64
import copy
import difflib
import json
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
        class_commands.add_argument('-i', '--input', help='The input template created with the AppDynamics UI',
                                    required=True)
        class_commands.add_argument('-o', '--output', help='The output file.')
        class_commands.add_argument('-p', '--prettify', help='Prettify the json output', action='store_true')
        class_commands.add_argument('-v', '--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('-n', '--name', help='Set the name of the new dashboard', default=False)
        return class_commands

    @classmethod
    def run(cls, args, config):

        print('Dashboards run')
        # TODO replicate a dashboard with search and replace as a whole
        dash = Dashboards(config, args)
        if args.function == 'export':
            dash.export()

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

    def export(self):
        self.__set_request_logging()
        self._do_verbose_print('Doing dashboard Export...')
        if self.args.id is None:
            self._do_verbose_print('No dashboard id specified with --id, see --help')
            sys.exit()
        self._do_verbose_print(f'Attempting to export dashboard with id={self.args.id}')
        token = self.get_oauth_token()
        base_url = self.config['CONTROLLER_INFO']['base_url']
        headers = {"Authorization": "Bearer " + token}
        url = base_url + 'controller/CustomDashboardImportExportServlet?dashboardId=' + self.args.id + '&output=JSON'
        response = requests.get(url, headers=headers)
        ddata = response.json()
        d_file = ddata['name'].strip() + ".json"
        if self.args.output:
            d_file = self.args.output
        json_obj = json.dumps(ddata)
        with open(d_file, "w") as outfile:
            outfile.write(json_obj)
        return json_obj

    # Process the options. If an option is not set, return the default value
    def _get_option(self, option, default):
        if "options" not in self.builder_config:
            return default
        if option not in self.builder_config["options"]:
            return default
        return self.builder_config["options"][option]

    def _get_builder_config(self):
        if self.args.builder_config:
            self.builder_config = json.loads(open(self.args.builder_config, "r").read())
            return
        self._do_verbose_print('Using empty builder config since none specified, see --help')

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

    # The following function is the "main" method processing a dashboard search/replace
    def _repeat_dashboard(self, dashboard):
        # Should the existing dashboard be replaced or should we extend the list?
        extendWidgets = self._get_option("extendWidgets", True)
        topOffset = self._get_option("topOffset", 0)
        leftOffset = self._get_option("leftOffset", 0)
        maxX, maxY, minX, minY = calculateDimensions(dashboard["widgetTemplates"])

        newWidgets = []
        i = 1 if extendWidgets else 0
        search = self._normalize_pattern(config["search"])
        # Walk over all search&replace patterns and create a new "row" for each of them.
        for replace in self._normalize_pattern(config["replace"]):
            yOffset = i * maxY + topOffset
            if (i + 1) * maxY + topOffset > dashboard["height"]:
                dashboard["height"] = (i + 1) * maxY + topOffset
            if reduce(lambda carry, element: carry and isinstance(element, list), replace, True):
                j = 0
                for column in replace:
                    xOffset = j * maxX + leftOffset
                    if (j + 1) * maxY + leftOffset > dashboard["width"]:
                        dashboard["width"] = (j + 1) * maxY + leftOffset
                    for widget in dashboard["widgetTemplates"]:
                        c = self._walk(copy.deepcopy(widget), search, column)
                        c["y"] += yOffset
                        c["x"] += xOffset
                        newWidgets.append(c)
                    j += 1
            else:
                for widget in dashboard["widgetTemplates"]:
                    c = self._walk(copy.deepcopy(widget), search, replace)
                    c["y"] += yOffset
                    newWidgets.append(c)
            i += 1

        if (extendWidgets):
            dashboard["widgetTemplates"].extend(newWidgets)
        else:
            dashboard["widgetTemplates"] = newWidgets

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
        builder_config = self._get_builder_config()
        source_dash = None
        if self.args.input:
            self._do_verbose_print('--input specified so using that, see --help')
            source_dash = json.loads(open(self.args.input, "r").read())
        else:
            self._do_verbose_print('--id specified so calling export, see --help')
            source_dash = self.export()
        if source_dash is None:
            self._do_verbose_print('--id or --input was not specified so exiting, see --help')
            return
