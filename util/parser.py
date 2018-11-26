# -*- coding: utf-8 -*-
"""
Parser implementations are responsible for config file parsing.

A parser consists of a parse function which receives a config file and
returns all possible configurations based on the content. For example, if a
config file is a JSON string such as:

    {
      "gcloud_version":[
        "226.0.0-slim"
      ],
      "node_version":[
        "8.0.0",
        "9.11.2"
      ],
      "version":"node_version"
    }

then this denotes two different configurations:

    {
      "gcloud_version":"226.0.0-slim",
      "node_version":"8.0.0",
      "version":"node_version"
    }

and

    {
      "gcloud_version":"226.0.0-slim",
      "node_version":"9.11.2",
      "version":"node_version"
    }
"""
import itertools
import json


def parse(config_path):
    """
    Parses the content of the config file and returns all possible
    configurations.
    :param config_path: the path of the config file.
    :return: configurations iterable.
    """
    with open(config_path, 'r') as cfg:
        content = json.load(cfg)
    unicodes, lists = _collect(content)
    for dictionary in _cross_product(lists):
        dictionary.update(unicodes)
        yield dictionary


def _collect(content):
    unicodes = {}
    lists = {}
    for key, value in content.iteritems():
        if isinstance(value, unicode):
            unicodes[key] = value
        elif isinstance(value, list):
            lists[key] = value
        else:
            raise Exception("unsupported type: '{}'".format(type(value)))
    return unicodes, lists


def _cross_product(dictionary):
    keys = dictionary.keys()
    values = dictionary.values()
    for product in itertools.product(*values):
        yield dict(zip(keys, product))
