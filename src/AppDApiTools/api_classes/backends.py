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
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
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
        if self.args.name is None:
            print('this function requires --name for application')
            return {}
        token = self.get_oauth_token()
        base_url = self.config['CONTROLLER_INFO']['base_url']
        headers = {"Authorization": "Bearer " + token}
        url = base_url + 'controller/rest/applications/' + self.args.name + '/backends?output=JSON'
        response = requests.get(url, headers=headers)
        self.do_verbose_print(response.json())
        if self.args.output is not None:
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

    def build_json_list(self, data={}, config_keys=[], entity_keys=[]):
        ndata = []
        # loop through data['entities'][1][x]
        for i in range(len(data['entities'][1])):
            entity_columns = {}
            if len(entity_keys) > 0:
                # lets check non recursively before diving into config
                for ek in entity_keys:
                    if ek in data['entities'][1][i][1]:
                        entity_columns[ek] = data['entities'][1][i][1][ek]
            # print(columns)
            for x in range(len(data['entities'][1][i][1]['configs'][1])):
                columns = {}
                for k in config_keys:
                    vals = []
                    # print(k[1])
                    # print(data['entities'][1][i][1])
                    # recursive search keys in data['entities'][1][x][1]
                    vals = self._parse_json_recursively_multi(data['entities'][1][i][1]['configs'][1][x], k[0], vals)
                    # print(vals)
                    if len(vals) > k[1]:
                        columns[k[0]] = vals[k[1]]
                    # print(r)
                    # if r is not None:
                    #     columns[k] = r[1]
                # print(columns)
                ndata.append(entity_columns | columns)
        print(ndata)

        return ndata
