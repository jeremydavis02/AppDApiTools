import argparse
import configparser
import importlib
import logging
import pkgutil
import sys

from AppDApiTools import api_classes
from AppDApiTools.api_classes import api_base

config = configparser.ConfigParser()
config.read('config.ini')


logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True


def do_work():
    # Use a breakpoint in the code line below to debug your script.
    parser = argparse.ArgumentParser(description='AppDynamics API Tooling.')
    package = api_classes
    for (module_loader, name, ispkg) in pkgutil.iter_modules(package.__path__):
        print(module_loader)
        print(name)
        print(ispkg)
        importlib.import_module('.' + name, 'api_classes')

    all_my_base_classes = {cls.__name__: cls for cls in api_base.ApiBase.__subclasses__()}
    print(all_my_base_classes)
    sub_parser = parser.add_subparsers(dest='subparser_name', help='sub commands help')
    for k, v in all_my_base_classes.items():
        mods = importlib.import_module('api_classes.' + k.lower())
        print(mods)
        c = getattr(mods, k)
        c.get_function_parms(sub_parser)

    args = parser.parse_args()
    if args.subparser_name is None:
        sys.stderr.write('No Api Group Specified!')
        parser.print_help()
        sys.exit(2)
    api_class_ref = getattr(importlib.import_module('api_classes.' + args.subparser_name.lower()), args.subparser_name)
    print(args.subparser_name)
    api_class_ref.run(args, config)


if __name__ == '__main__':
    do_work()
