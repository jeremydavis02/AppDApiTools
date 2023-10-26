import argparse
import configparser
import importlib
import pkgutil
import sys
import os
from cryptography.fernet import Fernet
from getpass import getpass
import AppDApiTools
from AppDApiTools import api_classes
from AppDApiTools.api_classes import api_base


def build_config(args=None):
    #print("in build config")
    new_config = configparser.ConfigParser(allow_no_value=True)
    #print(os.path.join(os.path.dirname(__file__), 'config', 'sample-config.ini'))

    new_config.read(os.path.join(os.path.dirname(__file__), 'config', 'sample-config.ini'))
    # copy the template to drive the loop with
    template_config = new_config
    # print(new_config.sections())
    build_section = True
    section_count = 0
    new_or_append = 'w'
    if args is not None and args.add_section:
        # make sure we append not overwrite
        new_or_append = 'a'
        # also we need to remove the base new config sections so they don't duplicate
        new_config.remove_section("CONTROLLER_INFO")
        new_config.remove_section("SYNTH_INFO")
    while build_section:
        section_prefix = ""
        if section_count <= 0 and (args is not None and not args.add_section):
            print(f'First configuration will be used as default when no system configuration is specified. (Recommend using test for default)')
        else:
            section_prefix = input(f'Specify system prefix (test|prod|main) any controller system string, no dashes (-) :')+'-'
        for section in template_config.sections():
            full_section = section_prefix+section
            if full_section not in new_config.sections():
                new_config.add_section(full_section)
            for k, v in template_config.items(section):
                # TODO somehow we are picking up psw on second iteration here.
                new_val = input(f'For section [{full_section}] please specify {k} :')
                new_config.set(section=full_section, option=k, value=new_val)
        crypt_key = Fernet.generate_key()

        secret_pass = getpass(f'Input your user password, which will be encrypted in config: ')
        fcrypt = Fernet(crypt_key)
        crypted_password = fcrypt.encrypt(str.encode(secret_pass))
        new_config.set(section=section_prefix+"CONTROLLER_INFO", option="psw", value=str(crypted_password, 'UTF-8'))
        new_config.set(section=section_prefix+"CONTROLLER_INFO", option="key", value=str(crypt_key, 'UTF-8'))
        another = input(f'Create another system configuration? (True|False) :')
        if another.capitalize() == 'False':
            build_section = False
        section_count = section_count + 1

    with open(os.path.join(os.path.dirname(__file__), 'config', 'config.ini'), new_or_append) as c_file:
        new_config.write(c_file)

    sys.exit()


def do_work():
    # Use a breakpoint in the code line below to debug your script.
    parser = argparse.ArgumentParser(description='AppDynamics API Tooling.')
    parser.add_argument("--config", help="create or update config", action="store_true")
    parser.add_argument("--add_section", help="add a new controller config to existing", action="store_true")
    package = api_classes
    for (module_loader, name, ispkg) in pkgutil.iter_modules(package.__path__):
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
        build_config(args)
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
