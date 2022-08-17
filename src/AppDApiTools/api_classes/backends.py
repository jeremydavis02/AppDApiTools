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
            'get_list',
        ]
        class_commands = subparser.add_parser('Backends', help='Synthetics commands')
        class_commands.add_argument('function', choices=functions, help='The Backend api function to run')
        class_commands.add_argument('--name', help='Specific synthetic job name')
        class_commands.add_argument('--appkey', help='Specific appkey synthetic jobs')
        return class_commands

    @classmethod
    def run(cls, args, config):
        print('Synthetics run')

        # create instance of yourself
        backends = Backends(config, args)
        print(args.function)
        if args.function == 'get_list':
            backends.get_list()

    def __init__(self, config, args):
        super().__init__(config, args)

    def get_list(self, out_file=None):
        if self.args.name is None:
            print('this function requires --name for application')
            return {}
        token = self.get_oauth_token()
        base_url = self.config['CONTROLLER_INFO']['base_url']
        headers = {"Authorization": "Bearer " + token}
        url = base_url + 'controller/rest/applications/' + self.args.name + '/backends?output=JSON'
        response = requests.get(url, headers=headers)
        print(response.json())
        if out_file is not None:
            fp = open(out_file, 'w')
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
