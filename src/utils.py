#!/usr/bin/env python

import coloredlogs
import functools
import logging
import time
import os
import sys



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


# This class could be imported from a utility module
class LoggingClass(object):
    @property
    def logger(self):
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(pathname)s : %(lineno)d - %(message)s"
        name = ".".join([os.path.basename(sys.argv[0]), self.__class__.__name__])
        logging.basicConfig(format=log_format)
        coloredlogs.install(fmt=log_format)
        return logging.getLogger(name)


