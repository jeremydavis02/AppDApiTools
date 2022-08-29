#!/usr/local/bin/python
from __future__ import print_function

import argparse
import base64
import copy
import difflib
import json
import re
from functools import reduce


def buildConfig(config):
    if config:
        return json.loads(open(config, "r").read())

    return {"search": [], "replace": []}


# Source: http://stackoverflow.com/questions/774316/python-difflib-highlighting-differences-inline
def show_diff(old, new):
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


# Process a single property of a widget
def processWidgetProperty(prop, key, search, replace, verbose):
    # Walk recursively if the property is a list or dict
    if isinstance(prop, (dict, list)):
        return walk(prop, search, replace, verbose)

    old = prop
    for i in range(len(search)):
        prop = searchAndReplace(search[i], key, replace[i], prop)

    if verbose >= 3 and old != prop:
        print(show_diff(old, prop))

    return prop


# Apply search and replace patterns onto a value
def searchAndReplace(search, key, replace, target):
    if "key" in search and search["key"] != key:
        return target

    if "regex" in search and search["regex"]:
        return re.sub(re.compile(search["value"]), replace["value"], target)

    if hasattr(target, "replace"):
        return target.replace(str(search["value"]), str(replace["value"]))

    # if isinstance(target, (int,long)):
    if isinstance(target, (int, int)):
        return replace["value"] if target == search["value"] else target


# Recursively walk through the widget tree and apply the search&replace patterns
def walk(widget, search, replace, verbose):
    for key in widget if isinstance(widget, dict) else range(len(widget)):
        widget[key] = processWidgetProperty(widget[key], key, search, replace, verbose)

    return widget


# Process the options. If an option is not set, return the default value
def getOption(config, option, default):
    if not "options" in config:
        return default
    if not option in config["options"]:
        return default
    return config["options"][option]


# Calculate the dimensions of a AppDynamics dashboard
def calculateDimensions(widgetTemplates):
    maxX = 0  # height
    maxY = 0  # width
    minX = dashboard["width"]
    minY = dashboard["height"]

    # Compute the dimension of the current dashboard
    for widget in widgetTemplates:
        maxY = widget["y"] + widget["height"] if widget["y"] + widget["height"] > maxY else maxY
        minX = widget["x"] if widget["x"] < minX else minX
        minY = widget["y"] if widget["y"] < minY else minY
        maxX = widget["x"] + widget["width"] if widget["x"] + widget["width"] > maxX else maxX

    return (maxX, maxY, minX, minY)


def normalizePattern(pattern):
    if isinstance(pattern, list):
        for i in range(len(pattern)):
            pattern[i] = normalizePattern(pattern[i])
        return pattern

    if not isinstance(pattern, dict):
        return {"value": pattern, "regex": False}

    if not "regex" in pattern:
        pattern["regex"] = False

    if "func" in pattern and pattern["func"] == "base64image":
        pattern["value"] = "data:image/png;base64," + base64.b64encode(open(pattern["value"], "rb").read())

    return pattern


# The following function is the "main" method processing a dashboard
def repeatDashboard(dashboard, config, verbose):
    # Should the existing dashboard be replaced or should we extend the list?
    extendWidgets = getOption(config, "extendWidgets", True)
    topOffset = getOption(config, "topOffset", 0)
    leftOffset = getOption(config, "leftOffset", 0)
    maxX, maxY, minX, minY = calculateDimensions(dashboard["widgetTemplates"])

    newWidgets = []
    i = 1 if extendWidgets else 0
    search = normalizePattern(config["search"])
    # Walk over all search&replace patterns and create a new "row" for each of them.
    for replace in normalizePattern(config["replace"]):
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
                    c = walk(copy.deepcopy(widget), search, column, verbose)
                    c["y"] += yOffset
                    c["x"] += xOffset
                    newWidgets.append(c)
                j += 1;
        else:
            for widget in dashboard["widgetTemplates"]:
                c = walk(copy.deepcopy(widget), search, replace, verbose)
                c["y"] += yOffset
                newWidgets.append(c)
        i += 1

    if (extendWidgets):
        dashboard["widgetTemplates"].extend(newWidgets)
    else:
        dashboard["widgetTemplates"] = newWidgets

    return dashboard


parser = argparse.ArgumentParser(description="Build large AppDynamics dashboard from a small input template.")

parser.add_argument('-c', '--config', help='The configuration describing how to build the new dashboard. ',
                    required=False)
parser.add_argument('-i', '--input', help='The input template created with the AppDynamics UI', required=True)
parser.add_argument('-o', '--output', help='The output file. Use "-" for stdout')
parser.add_argument('-p', '--prettify', help='Prettify the json output', action='store_true')
parser.add_argument('-v', '--verbose', help='Enable verbose output', action='count', default=0)
parser.add_argument('-n', '--name', help='Set the name of the new dashboard', default=False)

args = parser.parse_args()

dashboard = json.loads(open(args.input, "r").read())

config = buildConfig(args.config)

newDashboard = repeatDashboard(dashboard, config, args.verbose)

if args.verbose >= 1:
    print("New Dimensions:", newDashboard["width"], "x", newDashboard["height"])

if args.name != False:
    newDashboard["name"] = args.name

result = json.dumps(newDashboard, sort_keys=args.prettify, indent=4 if args.prettify else None)

if args.output == "-":
    print(result)
elif args.output:
    newFile = open(args.output, "w")
    newFile.write(result);
