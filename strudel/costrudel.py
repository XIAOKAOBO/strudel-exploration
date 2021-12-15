# this is the implementation of line classification version of strudel.
# Created by lan at 2020/3/2
# import logging
import string
from functools import reduce

import numpy as np
import pandas as pd
import rolling
from nltk import word_tokenize
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import ndcg_score
from collections import Counter

from strudel.derived_detector import detect_derived_cells
from strudel.lstrudel import LStrudel
from strudel.utility import is_numeric, detect_datatype, calculate_hist_diff



def is_empty_row(row):
    return all([True if cell.strip() == '' else False for cell in row])


def create_column_feature_vector(file_json_dict):
    file_array_t = np.array(file_json_dict['table_array'])
    file_array = pd.DataFrame(file_array_t)
    tname  = file_json_dict['file_name']
    tid = file_json_dict['table_id']    
    column_number = np.array(range(file_array.shape[1]))
    labels1 = np.array(file_json_dict['annotations']).transpose()
    
    def most_common(row):
        # rowt = np.delete(row,np.where(row=='empty'))
        # if len(rowt) < 1:
        #     print('is data')
        #     return 'data'
        c = Counter(row)
        value = c.most_common(1)[0][0]
        if value == None:
            return 'empty'
        # print('is '+value)c
        return value

    labels = np.apply_along_axis(func1d=most_common,axis=1,arr=labels1)
    # print(labels.shape)

    aggregation_keywords = ['sum', 'percentage', 'total', 'average', 'avg']

    num_lookup_lines = 5

    def has_aggregation_keyword(row):
        tokens = map(lambda w: w.lower(), reduce(list.__add__, [word_tokenize(cell) for cell in row]))
        kw_exist = 1 if len(set(tokens).intersection(aggregation_keywords)) > 0 else 0
        return kw_exist

    f_kw_exist = np.apply_along_axis(func1d=has_aggregation_keyword, axis=0, arr=file_array_t)

    def row_emptiness_pattern(row):
        pattern = np.array([1 if len(cell.strip()) != 0 else 0 for cell in row])
        return pattern

    def discounted_cumulative_gain(row):
        # We hope all "1" are at the left of a pattern to all "0". Translating it to a dcg calculation,
        # an element's relevance is always 1 more than the element to its right, and the right-most element has a relevance score of 1.
        # For example, given a pattern [1,1,0,1,0,0], the relevance of the sequence is [6,5,4,3,2,1]
        # For an ideal pattern, the relevance of all "1" is large than that of all "0".
        re_pattern = np.asarray([row_emptiness_pattern(row)])
        pattern_len = re_pattern.shape[1]
        relevance = np.asarray([[pattern_len - index for index in range(0, pattern_len)]])
        n_dcg = ndcg_score(re_pattern, relevance)
        return n_dcg

    f_dcg = np.apply_along_axis(func1d=discounted_cumulative_gain, axis=0,arr=file_array_t)

    num_lines = len(file_array.columns)
    f_column_position = []
    for index, row in enumerate(file_array):
        f_column_position.append((index + 1) / num_lines)
    f_column_position = np.array(f_column_position)

    def empty_cell_ratio(row):
        re_pattern = row_emptiness_pattern(row)
        empty_cell_ratio = 1 - np.count_nonzero(re_pattern) / len(row)
        return empty_cell_ratio

    f_empty_cell_ratio = np.apply_along_axis(func1d=empty_cell_ratio, axis=0,arr=file_array_t)

    def numeric_cell_ratio(row):
        nc_ratio = len([cell for cell in row if is_numeric(cell)]) / len(row)
        return nc_ratio

    f_numeric_cell_ratio = np.apply_along_axis(func1d=numeric_cell_ratio, axis=0,arr=file_array_t)

    def string_cell_ratio(row):
        sc_ratio = len([cell for cell in row if detect_datatype(cell) == 4]) / len(row)
        return sc_ratio

    f_string_cell_ratio = np.apply_along_axis(func1d=string_cell_ratio, axis=0,arr=file_array_t)

    def average_word_count(row):
        cell_tokens = [list(filter(lambda token: token not in string.punctuation, word_tokenize(cell))) for cell in row]
        len_cell_tokens = [len(tokens) for tokens in cell_tokens if len(tokens) > 0]
        if not len_cell_tokens:
            awc = 0.0
        else:
            awc = np.sum(len_cell_tokens) / len(len_cell_tokens)
        return awc

    f_average_word_count = np.apply_along_axis(func1d=average_word_count, axis=0,arr=file_array_t)

    # def empty_column_ratio_after(window):
    #     row_window = window[0]
    #     rows_after = row_window[1:]
    #     empty_rows_after = [row_after for row_after in rows_after if is_empty_row(row_after)]
    #     if not rows_after:
    #         ratio = 0.0
    #     else:
    #         ratio = len(empty_rows_after) / len(rows_after)
    #     return ratio

    # windows = list(rolling.Apply(file_array, num_lookup_lines + 1, operation=list, window_type='variable'))
    # windows = np.array([windows[:len(windows) - len(file_array)]], dtype=object).transpose()
    # print(windows.shape)

    # f_empty_column_ratio_after = file_array.apply(func=empty_column_ratio_after, window=windows,  axis=0)

    def empty_line_ratio_after(window):
        row_window = window[0]
        rows_after = row_window[1:] #np.array(file_array.loc[:,row_window[1:]]).transpose()
        empty_rows_after = [row_after for row_after in rows_after if is_empty_row(row_after)]
        if  not rows_after:
            ratio = 0.0
        else:
            ratio = len(empty_rows_after) / len(rows_after)
        return ratio

    windows = list(rolling.Apply(file_array_t.transpose(), num_lookup_lines + 1, operation=list, window_type='variable'))
    windows = np.array([windows[len(windows) - len(file_array.columns):]], dtype=object).transpose()

    f_empty_column_ratio_after = np.apply_along_axis(func1d=empty_line_ratio_after, axis=1, arr=windows)

    def empty_column_ratio_before(window):
        row_window = window[0]
        rows_before = row_window[:-1]
        empty_row_before = [row_before for row_before in rows_before if is_empty_row(row_before)]
        if not rows_before:
            ratio = 0.0
        else:
            ratio = len(empty_row_before) / len(rows_before)
        return ratio

    windows = list(rolling.Apply(file_array_t.transpose(), num_lookup_lines + 1, operation=list, window_type='variable'))
    windows = np.array([windows[:len(file_array.columns)]], dtype=object).transpose()

    f_empty_column_ratio_before = np.apply_along_axis(func1d=empty_column_ratio_before, axis=1, arr=windows)

    def hist_diff_after(window):
        row_window = window[0]
        row = row_window[0]
        row_value_length = [len(cell.strip()) for cell in row]
        rows_after = row_window[1:]
        hist_diff = 0.0
        for row_after in rows_after:
            if is_empty_row(row_after):
                continue
            row_after_value_length = [len(cell.strip()) for cell in row_after]
            hist_diff = calculate_hist_diff(row_value_length, row_after_value_length)
            break
        return hist_diff

    windows = list(rolling.Apply(file_array_t.transpose(), num_lookup_lines + 1, operation=list, window_type='variable'))
    windows = np.array([windows[-len(file_array.columns):]], dtype=object).transpose()

    # f_hist_diff_after = file_array.apply(func1d=hist_diff_after, axis=0, window=windows)
    f_hist_diff_after = np.apply_along_axis(func1d=hist_diff_after, axis=1, arr=windows)

    def hist_diff_before(window):
        row_window = window[0]
        row = row_window[-1]
        row_value_length = [len(cell.strip()) for cell in row]
        rows_before = row_window[:-1]
        hist_diff = 0.0
        for row_before in reversed(rows_before):
            if is_empty_row(row_before):
                continue
            row_before_value_length = [len(cell.strip()) for cell in row_before]
            hist_diff = calculate_hist_diff(row_value_length, row_before_value_length)
            break
        return hist_diff

    windows = list(rolling.Apply(file_array_t.transpose(), num_lookup_lines + 1, operation=list, window_type='variable'))
    windows = np.array([windows[:len(file_array.columns)]], dtype=object).transpose()

    f_hist_diff_before = np.apply_along_axis(func1d=hist_diff_before, axis=1, arr=windows)

    def data_type_after(window):
        row_window = window[0]
        row = row_window[0]
        row_data_type = [detect_datatype(cell) for cell in row]
        rows_after = row_window[1:]
        data_type_same_ratio = 0.0
        for row_after in rows_after:
            if is_empty_row(row_after):
                continue
            row_after_data_type = [detect_datatype(cell) for cell in row_after]
            cell_same_data_type = [(this_cell, that_cell) for this_cell, that_cell in zip(row_data_type, row_after_data_type) if this_cell == that_cell]
            data_type_same_ratio = len(cell_same_data_type) / len(row_data_type)
        return data_type_same_ratio

    windows = list(rolling.Apply(file_array_t.transpose(), num_lookup_lines + 1, operation=list, window_type='variable'))
    windows = np.array([windows[-len(file_array.columns):]], dtype=object).transpose()

    f_data_type_after = np.apply_along_axis(func1d=data_type_after, axis=1, arr=windows)

    def data_type_before(window):
        row_window = window[0]
        row = row_window[-1]
        row_data_type = [detect_datatype(cell) for cell in row]
        rows_before = row_window[:-1]
        data_type_same_ratio = 0.0
        for row_before in rows_before:
            if is_empty_row(row_before):
                continue
            row_before_data_type = [detect_datatype(cell) for cell in row_before]
            cell_same_data_type = [(this_cell, that_cell) for this_cell, that_cell in zip(row_data_type, row_before_data_type) if this_cell == that_cell]
            data_type_same_ratio = len(cell_same_data_type) / len(row_data_type)
        return data_type_same_ratio

    windows = list(rolling.Apply(file_array_t.transpose(), num_lookup_lines + 1, operation=list, window_type='variable'))
    windows = np.array([windows[:len(file_array.columns)]], dtype=object).transpose()

    f_data_type_before = np.apply_along_axis(func1d=data_type_before, axis=1, arr=windows)

    is_derived_file_array, _ = detect_derived_cells(file_array_t.transpose())

    f_derived_cell_coverage = []
    for row, is_derived_row in zip(file_array_t.transpose(), is_derived_file_array):
        num_is_derived = len([cell for cell in is_derived_row if cell == 'd'])
        num_numeric = len([cell for cell in row if is_numeric(cell)])
        coverage = num_is_derived / num_numeric if num_numeric != 0 else 0.0
        f_derived_cell_coverage.append(coverage)
    f_derived_cell_coverage = np.array(f_derived_cell_coverage)
    
    # print(f_derived_cell_coverage.shape)
    # print(file_json_dict['file_name']+' '+file_json_dict['table_id'] +' '+str(column_number))
    # print(labels.shape)
    # print(f_hist_diff_after.shape)
    # print(f_hist_diff_before.shape)
    # print(f_kw_exist.shape)
    # print(labels.shape)
    # print(f_data_type_after.shape)
    # print('yes')

    # print({'file_name': tname,
    #                                             'sheet_name': tid,
    #                                             'column_number': column_number,
    #                                             'column_position': f_column_position,
    #                                             'has_derived_keyword': f_kw_exist,
    #                                             'discounted_cumulative_gain': f_dcg,
    #                                             'line_empty_cell_ratio': f_empty_cell_ratio,
    #                                             'line_numeric_cell_ratio': f_numeric_cell_ratio,
    #                                             'line_string_cell_ratio': f_string_cell_ratio,
    #                                             'line_average_word_count': f_average_word_count,
    #                                             'empty_column_ratio_after': f_empty_column_ratio_after,
    #                                             'empty_column_ratio_before': f_empty_column_ratio_before,
    #                                             'hist_diff_after': f_hist_diff_after,
    #                                             'hist_diff_before': f_hist_diff_before,
    #                                             'data_type_after': f_data_type_after,
    #                                             'data_type_before': f_data_type_before,
    #                                             'derived_cell_coverage': f_derived_cell_coverage})
    # print(num_lines)
    # print(labels.shape)
    # print('yes')
    
    # temp = {'file_name': tname,
    #                                             'file_name': file_json_dict['file_name'],
    #                                             'sheet_name': file_json_dict['table_id'],
    #                                             'column_position': f_column_position,
    #                                             'has_derived_keyword': f_kw_exist,
    #                                             'discounted_cumulative_gain': f_dcg,
    #                                             'line_empty_cell_ratio': f_empty_cell_ratio,
    #                                             'line_numeric_cell_ratio': f_numeric_cell_ratio,
    #                                             'line_string_cell_ratio': f_string_cell_ratio,
    #                                             'line_average_word_count': f_average_word_count,
    #                                             'empty_column_ratio_after': f_empty_column_ratio_after,
    #                                             'empty_column_ratio_before': f_empty_column_ratio_before,
    #                                             'hist_diff_after': f_hist_diff_after,
    #                                             'hist_diff_before': f_hist_diff_before,
    #                                             'data_type_after': f_data_type_after,
    #                                             'data_type_before': f_data_type_before,
    #                                             'derived_cell_coverage': f_derived_cell_coverage,
    #                                             'labels': labels}
    # # print(len(temp))
    # for item in temp:
    #     print(temp[item])
    # print('ues')
   
    # lstrudel_feature_vector = pd.DataFrame.from_dict(temp)
    # return pd.DataFrame(data=temp).transpose()
    lstrudel_feature_vector = pd.DataFrame({'file_name': file_json_dict['file_name'],
                                                'sheet_name': file_json_dict['table_id'],
                                                'column_number': column_number,
                                                'column_position': f_column_position,
                                                'column_has_derived_keyword': f_kw_exist,
                                                'column_discounted_cumulative_gain': f_dcg,
                                                'column_empty_cell_ratio': f_empty_cell_ratio,
                                                'column_numeric_cell_ratio': f_numeric_cell_ratio,
                                                'column_string_cell_ratio': f_string_cell_ratio,
                                                'column_average_word_count': f_average_word_count,
                                                'empty_column_ratio_after': f_empty_column_ratio_after,
                                                'empty_column_ratio_before': f_empty_column_ratio_before,
                                                'column_hist_diff_after': f_hist_diff_after,
                                                'column_hist_diff_before': f_hist_diff_before,
                                                'column_data_type_after': f_data_type_after,
                                                'column_data_type_before': f_data_type_before,
                                                'column_derived_cell_coverage': f_derived_cell_coverage,
                                                'label': labels})
    # for i in lstrudel_feature_vector:
    #     print(lstrudel_feature_vector[i])
    return lstrudel_feature_vector


def create_feature_vector(dataset_name, feature_vector_path):
    """
    create the feature vector from the input data files.

    :param dataset_name: the name of datasets used for experiments.
    # :param data_path: the path that stores data files, each file is a single csv file.
    :return: feature vector with label for all data files, each line for a single csv file
    """
    if dataset_name == 'all':
        line_feature_vector_path = feature_vector_path + 'all/training.csv'
        line_metadata_path = feature_vector_path + 'all/metadata.csv'
    else:
        line_feature_vector_path = feature_vector_path + dataset_name + '/training.csv'
        line_metadata_path = feature_vector_path + dataset_name + '/metadata.csv'

    line_feature_vector_df = pd.read_csv(line_feature_vector_path)
    line_metadata_df = pd.read_csv(line_metadata_path)

    # create is derived line feature from the cell feature file.
    cell_feature_path = '../feature_vec/cstrudel/' + dataset_name + ".csv"
    cell_feature_df = pd.read_csv(cell_feature_path)[['is_sum', 'filename', 'sheetname', 'row']]
    groups = cell_feature_df.groupby(['filename', 'sheetname', 'row'])
    is_sum_amount = []
    for index, group in groups:
        is_sum_amount.append([index[0], index[1], index[2], group[group['is_sum'] == 1].size / group.size])
    is_sum_amount_df = pd.DataFrame(data=is_sum_amount, columns=['filename', 'sheetname', 'row', 'is_sum_ratio'])

    return line_feature_vector_df, line_metadata_df, is_sum_amount_df

    # return line_feature_vector_df, line_metadata_df, None


class COStrudel:
    algo_name = 'costrudel'

    def __init__(self, n_jobs=1):
        self.n_jobs = n_jobs

    def fit(self, train_set: pd.DataFrame, test_set: pd.DataFrame, method='predict_proba'):
        profile_columns = ['file_name', 'sheet_name', 'column_number']

        empty_line_removed_train_set = train_set[train_set['label'] != 'empty'].reset_index(drop=True)
        empty_line_removed_test_set = test_set[test_set['label'] != 'empty'].reset_index(drop=True)

        test_set_line_profile = empty_line_removed_test_set[profile_columns]

        clean_train_set = empty_line_removed_train_set.drop(profile_columns, axis=1)
        clean_test_set = empty_line_removed_test_set.drop(profile_columns, axis=1)

        X_train = clean_train_set.iloc[:, 0:len(clean_train_set.columns)-1]
        y_train = clean_train_set.iloc[:, len(clean_train_set.columns) - 1:len(clean_train_set.columns)]

        X_test = clean_test_set.iloc[:, 0:len(clean_test_set.columns)-1]
        y_test = clean_test_set.iloc[:, len(clean_test_set.columns) - 1: len(clean_test_set.columns)]

        clf = RandomForestClassifier(n_jobs=self.n_jobs)

        clf.fit(X_train, np.ravel(y_train))

        pred_prob = clf.predict_proba(X_test)
        pred_prob[np.isnan(pred_prob)]=0

        pred_prob_df = pd.DataFrame(data=pred_prob, columns='col_'+clf.classes_ + '_prob')
        pred_prob_df = pred_prob_df.fillna(0)
        test_set_line_profil = test_set_line_profile.fillna(0)
        y_test = y_test.fillna(0)
        # for item in pred_prob_df:
        #     print(pred_prob_df[item])
        test_set_with_line_prob = pd.concat([test_set_line_profile, pred_prob_df, y_test], axis=1)

        return test_set_with_line_prob
