import csv
import json
import requests
import logging

from .api_base import ApiBase


class Backends(ApiBase):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

    @classmethod
    def get_function_parms(cls, subparser):
        #print('getFunctions')
        functions = [
            'list',
            'url_list'
        ]
        class_commands = subparser.add_parser('Backends', help='Synthetics commands')
        class_commands.add_argument('function', choices=functions, help='The Backend api function to run')
        class_commands.add_argument('--name', help='Specific application name')
        class_commands.add_argument('--output', help='The output file.')
        class_commands.add_argument('--csv_fields', help='The fields to output in csv from json along with main backend fields comma delimited')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--auth', help='The auth scheme.', choices=['key', 'user'], default='key')
        return class_commands

    @classmethod
    def run(cls, args, config):
        # create instance of yourself
        backends = Backends(config, args)
        if args.function == 'list':
            backends.get_list()
        if args.function == 'url_list':
            backends.get_url_list()

    def __init__(self, config, args):
        super().__init__(config, args)

    def get_url_list(self):
        output_reset = self.args.output
        self.args.output = None
        backend_list = self.get_list()
        self.args.output = output_reset
        url_list = []
        for backend in backend_list:
            if backend["exitPointType"] == "HTTP":
                for prop in backend["properties"]:
                    if prop["name"] == "URL":
                        url_list.append(prop["value"])
        url_list.sort()
        self.do_verbose_print(url_list)
        if self.args.output is not None:
            with open(self.args.output, 'w') as fp:
                fp.write('\n'.join(url_list))
        return url_list

    def get_list(self):
        self.set_request_logging()
        if self.args.name is None:
            print('this function requires --name for application')
            return {}
        base_url = self.config['CONTROLLER_INFO']['base_url']
        headers, auth = self.set_auth_headers()
        url = base_url + 'controller/rest/applications/' + self.args.name + '/backends?output=JSON'
        response = requests.get(url, auth=auth, headers=headers)
        self.do_verbose_print(response.json())
        if self.args.output is not None:
            if '.csv' in self.args.output:
                if self.args.csv_fields is None:
                    print('this function requires --csv_fields for csv output')
                    return {}
                self.make_csv(response.json(), self.args.csv_fields.split(","))
            else:
                fp = open(self.args.output, 'w')
                json.dump(response.json(), fp)
        return response.json()

    def _parse_json_recursively_multi(self, json_object, target_key, vals=[]):
        if type(json_object) is dict and json_object:
            for key in json_object:
                if key == target_key:
                    # print("{}: {}".format(target_key, json_object[key]))
                    vals.append(json_object[key])
                vals = self._parse_json_recursively_multi(json_object[key], target_key, vals)

        elif type(json_object) is list and json_object:
            for item in json_object:
                vals = self._parse_json_recursively_multi(item, target_key, vals)

        return vals

    def _build_json_list(self, data, fields):
        ndata = []
        # loop through backend list
        for i in range(len(data)):
            backend_columns = {}
            if len(fields) > 0:
                prop_columns = {}
                for bk in fields:
                    if bk in data[i]:
                        backend_columns[bk] = data[i][bk]
                # print(columns)
                for x in range(len(data[i]['properties'])):
                    for k in fields:
                        if data[i]['properties'][x]['name'] == k:
                            prop_columns[data[i]['properties'][x]['name']] = data[i]['properties'][x]['value']

                ndata.append(backend_columns | prop_columns)
        print(ndata)
        return ndata

    def make_csv(self, data, fields):

        records = self._build_json_list(data, fields)
        with open(self.args.output, 'w', newline='') as csvfile:
            backend_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            # write header
            header = fields
            backend_writer.writerow(header)
            for r in records:
                print(r)
                backend_writer.writerow(r.values())
