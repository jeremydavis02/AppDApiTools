import json
import requests
import logging
from .api_base import ApiBase


class Dashboards(ApiBase):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

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
        class_commands.add_argument('--export_file', help='Specific path and filename for dashboard export otherwise dashboard name in current directory')
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

    def export(self):
        print('Doing dashboard Export...')
        if self.args.id is None:
            return
        print(f'Attempting to export dashboard with id={self.args.id}')
        token = self.get_oauth_token()
        base_url = self.config['CONTROLLER_INFO']['base_url']
        headers = {"Authorization": "Bearer " + token}
        url = base_url + 'controller/CustomDashboardImportExportServlet?dashboardId=' + self.args.id + '&output=JSON'
        response = requests.get(url, headers=headers)
        ddata = response.json()
        d_file = ddata['name'].strip()+".json"
        if self.args.export_file:
            d_file = self.args.export_file
        json_obj = json.dumps(ddata)
        with open(d_file, "w") as outfile:
            outfile.write(json_obj)
