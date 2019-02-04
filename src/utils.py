#!/usr/bin/env python

import coloredlogs
import logging
import os
import sys


# This class could be imported from a utility module
class LoggingClass(object):
    @property
    def logger(self):
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(pathname)s : %(lineno)d - %(message)s"
        name = ".".join([os.path.basename(sys.argv[0]), self.__class__.__name__])
        logging.basicConfig(format=log_format)
        coloredlogs.install(fmt=log_format)
        return logging.getLogger(name)


def combined_Dict_List(*args):
    """
    Combining two/more dictionaries into one with the same keys

    Params
    =======
    args: list
        list of dicts to combine

    Return
    =======
    result: dict
        combined dictionaries
    """
    result = {}
    for _dict in args:
        for key in result.viewkeys() | _dict.keys():
            if key in _dict:
                result.setdefault(key, []).extend([_dict[key]])
    return result


def merge_dicts(dict1, dict2):
    """
    Merge 2(Two) dictionaries into One
    """
    for key, value in dict2.iteritems():
        dict1.setdefault(key, []).extend(value)
    return dict1
    # merged_sensors = f_sensors.copy()
    # merged_sensors.update(x_sensors)
    # return merged_sensors

def swap_dict(_dict):
    """
    Swap keys and values of a dictionary
    """
    return dict((v, k) for k, v in _dict.iteritems())

def get_list_index(String, List):
        """
        Find the index of a string in a list

        Params
        =======
        String: str
            String to search in list
        List: list
            List to be searched!

        Return
        =======
        list
        """
        try:
            return [_c for _c, i in enumerate(List) if any(String in x for x in i)][0]
        except Exception:
            raise RuntimeError("Failed to find the index of string in list")
