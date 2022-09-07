import argparse
import configparser
import importlib
import pkgutil
import sys
import os
import AppDApiTools
from AppDApiTools import api_classes
from AppDApiTools.api_classes import api_base


def build_config():
    #print("in build config")
    new_config = configparser.ConfigParser(allow_no_value=True)
    #print(os.path.join(os.path.dirname(__file__), 'config', 'sample-config.ini'))
    new_config.read(os.path.join(os.path.dirname(__file__), 'config', 'sample-config.ini'))
    #print(new_config.sections())
    for section in new_config.sections():
        for k, v in new_config.items(section):
            new_val = input(f'For section [{section}] please specify {k} :')
            new_config.set(section=section, option=k, value=new_val)

    with open(os.path.join(os.path.dirname(__file__), 'config', 'config.ini'), 'w') as c_file:
        new_config.write(c_file)
    sys.exit()


def do_work():
    # Use a breakpoint in the code line below to debug your script.
    parser = argparse.ArgumentParser(description='AppDynamics API Tooling.')
    parser.add_argument("--config", help="create or update config", action="store_true")
    package = api_classes
    for (module_loader, name, ispkg) in pkgutil.iter_modules(package.__path__):
        #print(module_loader)
        #print(name)
        #print(ispkg)
        importlib.import_module('.' + name, 'AppDApiTools.api_classes')

    all_my_base_classes = {cls.__name__: cls for cls in api_base.ApiBase.__subclasses__()}
    #print(all_my_base_classes)
    sub_parser = parser.add_subparsers(dest='subparser_name', help='sub commands help')
    for k, v in all_my_base_classes.items():
        mods = importlib.import_module('AppDApiTools.api_classes.' + k.lower())
        #print(mods)
        c = getattr(mods, k)
        c.get_function_parms(sub_parser)

    args = parser.parse_args()
    if args.config:
        build_config()
        sys.exit()
    if args.subparser_name is None:
        sys.stderr.write('No Api Group Specified!')
        parser.print_help()
        sys.exit(2)
    api_class_ref = getattr(importlib.import_module('AppDApiTools.api_classes.' + args.subparser_name.lower()), args.subparser_name)
    #print(args.subparser_name)
    api_class_ref.run(args, config)


config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'config', 'config.ini'))
if not config.sections():
    # run config setup
    build_config()



if __name__ == '__main__':
    do_work()
