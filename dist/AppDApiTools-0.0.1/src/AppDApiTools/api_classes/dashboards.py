from .api_base import ApiBase


class Dashboards(ApiBase):

    @classmethod
    def get_function_parms(cls, subparser):
        print('getFunctions')
        functions = [
            'web_list',
            'api_list',
            'disable_web',
            'enable_web',
            'disable_api',
            'enable_api',
        ]
        class_commands = subparser.add_parser('Dashboards', help='Dashboards commands')
        class_commands.add_argument('function', choices=functions, help='The Dashboards api function to run')
        class_commands.add_argument('--name', help='Specific dashboard job name')
        return class_commands

    @classmethod
    def run(cls, args, config):
        print('Dashboards run')

    def __init__(self, config, args):
        super().__init__(config, args)
