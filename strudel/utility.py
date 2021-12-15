# Created by lan at 2021/11/9
from math import sqrt

import pandas

date_patterns = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%Y/%m/%d', '%y/%m/%d', '%d/%m/%y']
import datetime


def is_numeric(value):
    """
    check whether the given value is a numeric value. Numbers with decimal point or thousand separator can be properly determined.
    :param value: the given value to be verified
    :return: True if the given value is numeric
    """
    value_str = str(value).replace(',', '')
    try:
        float(value_str)
        return True
    except:
        return False


def to_numeric(value):
    if not is_numeric(value):
        raise Exception('Value is not numeric.')
    value_str = str(value).replace(',', '')
    try:
        return float(value_str)
    except:
        raise Exception('Conversion error.')


def isDate(value):
    _isDate = False
    for date_pattern in date_patterns:
        try:
           datetime.datetime.strptime(value, date_pattern)
           _isDate = True
           break
        except:
            pass
    return _isDate


def detect_datatype(value):
    """
    :param value: the value whose data type is to be checked.
    :return: 0 - 'date', 1 - 'float', 2 - 'int', 3 - 'empty', 4 - 'string', 5 - 'null'
    """
    if isDate(value):
        return 0
    try:
        float(value)
        return 1 if '.' in value else 2
    except:
        if len(value) == 0:
            return 3
        else:
            return 4


def calculate_hist_diff(hist1, hist2):
    total_sum = sum([sqrt(e1 * e2) for e1, e2 in zip(hist1, hist2)])

    factor = sqrt(sum(hist1) * sum(hist2))
    if factor != 0.0:
        bhattacharyya_factor = 1 / factor

        hd = 1 - bhattacharyya_factor * total_sum
        if hd > 0.0:
            hd = sqrt(hd)
        else:
            hd = 0.0
    else:
        hd = 0.0
    return hd


def process_pebble_results(results):
    line_fvs = [line_fv for line_fv in results]
    line_fv_dataset = pandas.concat(line_fvs)
    return line_fv_dataset

def cprocess_pebble_results(results):

    for item in results:
        # if item != None:
        print(type(item))
        print(item.shape)
        # for i in item:
        #     if i !='file_name' or i != 'sheet_name':
        #         print(i)
        #         print(item[i].shape)