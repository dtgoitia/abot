# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from json import JSONDecodeError

"""Configuration parameters for the bot, to be able to run them it's important to have them filled, it will raise an
error if they are not defined"""

import json
import os


def get_config(env_var: str, *args):
    """Get config parameter from file or environment var.

    :param str env_var: Environment var name, json key is derived from this
    :param args: This is a default value, if not defined, it will fail
    :return:
    """
    # First file
    value_holder = {}
    try:
        with open('test_config.json') as fd:
            file_config = json.load(fd)
        for k, v in file_config.items():
            if k.upper() == env_var:
                value_holder['value'] = v
    except Exception:
        pass
    # Second environment
    env_config = os.environ.get(env_var)
    if env_config is not None:
        try:
            value_holder['value'] = json.loads(env_config)
        except JSONDecodeError:
            value_holder['value'] = env_config
    if value_holder:
        return value_holder['value']
    if args:
        return args[0]
    raise EnvironmentError(f'Configuration {env_var} variable is not set by file or environment')
