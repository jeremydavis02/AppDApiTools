import json
import csv
import requests
import logging

json_data = {}


def get_list(base_url, token, application_name, out_file=None):
    headers = {"Authorization": "Bearer "+token}
    response = requests.get(base_url+'controller/rest/applications/'+application_name+'/backends?output=JSON', headers=headers)
    print(response.json())
    if out_file is not None:
        fp = open(out_file, 'w')
        json.dump(response.json(), fp)
    return response.json()


def load_file(file_path):
    f = open(file_path, 'r')
    return json.load(f)


def parse_json_recursively_multi(json_object, target_key, vals=[]):
    if type(json_object) is dict and json_object:
        for key in json_object:
            if key == target_key:
                #print("{}: {}".format(target_key, json_object[key]))
                vals.append(json_object[key])
            vals = parse_json_recursively_multi(json_object[key], target_key, vals)

    elif type(json_object) is list and json_object:
        for item in json_object:
            vals = parse_json_recursively_multi(item, target_key, vals)

    return vals


def parse_json_recursively(json_object, target_key, call_num: int):
    res = None
    #if target_key == 'matchPattern':
        #print(target_key)
        #print(type(json_object))
    # if type(json_object) is str and json_object:
    #     #print(json_object)
    #     #print(target_key)
    #     return (target_key, json_object)
    if type(json_object) is dict and json_object:
        for key in json_object:
            if key == target_key:
                print('FOUND IT')
                print(key)
                print(json_object[key])
                print(call_num)
                return target_key, json_object[key]
            r = parse_json_recursively(json_object[key], target_key, (call_num+1))
            if r is not None:
                return r

    elif type(json_object) is list and json_object:
        for item in json_object:
            r = parse_json_recursively(item, target_key, (call_num+1))
            if r is not None:
                return r

    #print(res)
    return res


def build_json_list(data={}, config_keys=[], entity_keys=[]):
    ndata = []
    #loop through data['entities'][1][x]
    for i in range(len(data['entities'][1])):
        entity_columns = {}
        if len(entity_keys) > 0:
            #lets check non recursively before diving into config
            for ek in entity_keys:
                if ek in data['entities'][1][i][1]:
                    entity_columns[ek] = data['entities'][1][i][1][ek]
        #print(columns)
        for x in range(len(data['entities'][1][i][1]['configs'][1])):
            columns = {}
            for k in config_keys:
                vals = []
                #print(k[1])
                #print(data['entities'][1][i][1])
                # recursive search keys in data['entities'][1][x][1]
                vals = parse_json_recursively_multi(data['entities'][1][i][1]['configs'][1][x], k[0], vals)
                #print(vals)
                if len(vals) > k[1]:
                    columns[k[0]] = vals[k[1]]
                # print(r)
                # if r is not None:
                #     columns[k] = r[1]
            #print(columns)
            ndata.append(entity_columns|columns)
    print(ndata)

    return ndata


def make_csv(data={}, keys=[], entity_keys=[], csv_path='backend-list.csv'):
    print(csv_path)
    records = build_json_list(data=data, config_keys=keys, entity_keys=entity_keys)
    with open(csv_path, 'w', newline='') as csvfile:
        backendwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        #write header
        header = []
        for ek in entity_keys:
            header.append(ek)
        for k in keys:
            header.append(k[0])
        backendwriter.writerow(header)
        for r in records:
            print(r)
            row = []
            for ek in entity_keys:
                if ek in r:
                    row.append((r[ek]))
            for k in keys:
                if k[0] in r:
                    row.append(r[k[0]])
            backendwriter.writerow(row)


