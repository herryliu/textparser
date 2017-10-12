#!/usr/bin/env python

import pprint

import textfsm
import clitable
import pandas as pd

TEMPLATE_INDEX_DIR = './template/'
TEMPLATE_INDEX_FILE = 'index'

class CliParser(clitable.CliTable):
    def __init__(self, index_file=TEMPLATE_INDEX_FILE,
            template_dir=TEMPLATE_INDEX_DIR, attributes=None):
        super(CliParser, self).__init__(index_file, template_dir)
        self.attributes = attributes
        self.cli_table = clitable.CliTable(TEMPLATE_INDEX_FILE, TEMPLATE_INDEX_DIR)

    def parse_cli(self, data=None):
        row = self.cli_table.index.GetRowMatch(self.attributes)
        print("row %s" % (self.index.index[row][0]))
        template_file = open(self.template_dir + self.index.index[row][0])
        if data == None:
            print("no data to parse")
            return None
        parser = textfsm.TextFSM(template_file)
        result = parser.ParseText(data)
        header = parser.header
        final_result = [header] + result
        print final_result
        return final_result

    def set_attribute(self, attributes):
        self.attributes = attributes

class DiffTable(object):
    @staticmethod
    def diff_generic(data_1, data_2, diff_conf):
        '''
        '''
        # check if data_1 and data_2 has same format
        if not DiffTable.check_data_format(data_1, data_2, diff_conf):
            return None

        # make index based on fields based on diff_conf
        t1 = pd.DataFrame(data=data_1[1:], columns=data_1[0])
        t2 = pd.DataFrame(data=data_2[1:], columns=data_2[0])

        index = diff_conf['index']
        # grouping the entries to make it all unique to index key
        grouping = diff_conf['grouping']
        if grouping:
            t1_grouped = t1.groupby(grouping)
            t2_grouped = t2.groupby(grouping)
        t1 = t1_grouped.agg(lambda x: set(x)).reset_index()
        t2 = t2_grouped.agg(lambda x: set(x)).reset_index()

        # make a outer join to formulate a table with all entreis
        result_table = pd.merge(t1, t2, on=index, how='outer', suffixes=['_L','_R'], indicator='DIFF_RESULT')

        # diff table convert to a list
        # insert a dummy column name at the front to match the merge operation
        result = [[''] + result_table.columns.tolist()] + result_table.reset_index().values.tolist()

        # find out which entry is new / missing / changed
        diff = DiffTable.get_diffs(result, diff_conf['check'])
        pprint.pprint(diff, width=2000)

        return diff

    @staticmethod
    def get_diffs(result, check):

        diff  = {'new': [],
                'missing': [],
                'changed': [],
                }
        # the column name is appended with _L or _R for non-index field
        all_column = result[0]
        # find all checking pair index according to column name
        full_index = [(all_column.index(c+'_L'), all_column.index(c+'_R')) for c in check]
        left_index = [x[0] for x in full_index]
        right_index = [x[1] for x in full_index]
        indicator_index = all_column.index('DIFF_RESULT')

        for r in result[1:]:
            if r[indicator_index] == 'left_only':
                #print("New Route: %s" % r)
                diff['new'].append(r)
                continue
            if r[indicator_index] == 'right_only':
                #print("Missing Route: %s" % r)
                diff['missing'].append(r)
                continue
            if r[indicator_index] == 'both':
                left = [r[i] for i in left_index]
                right = [r[i] for i in right_index]
                if not left == right:
                    #print("Changed Route: %s" % r)
                    diff['changed'].append(r)
        return diff

    @staticmethod
    def check_data_format(data_1, data_2, diff_conf):
        # check if the column name has the same contains
        if data_1[0] != data_2[0]:
            print('Column Name is not matching for those two data:\n data 1:%s \n data 2: %s' %
                  data_1, data_2)
            return False
        # check if the diff_conf using the right column name
        column_name = data_1[0]
        for conf in diff_conf.values():
            # check if conf is subset of column name
            if not frozenset(conf).issubset(frozenset(column_name)):
                print("diff_conf %s is not in %s" % (conf, column_name))
                return False
        return True


if __name__ == '__main__':

    attributes_1 = {'Command': 'show ip bgp summary', 'Vendor': 'Arista'}
    data_1 = '''BGP summary information for VRF default
Router identifier 10.30.95.2, local AS number 65200
Neighbor         V  AS      MsgRcvd   MsgSent  InQ OutQ  Up/Down State  PfxRcd PfxAcc
10.30.31.3       4  65200   8091068   7454502    0    0  170d15h Estab  48     48
10.30.47.1       4  65200   7467159   7454575    0    0  862d16h Estab  46     46
10.30.94.34      4  65202   4765404   3668243    0    0   13d16h Estab  5      5
'''
    parser = CliParser(attributes=attributes_1)
    result_1 = parser.parse_cli(data=data_1)

    attributes_2 = {'Command': 'show ip bgp summary', 'Vendor': 'Arista'}
    data_2 = '''BGP summary information for VRF default
Router identifier 10.30.95.2, local AS number 65200
Neighbor         V  AS      MsgRcvd   MsgSent  InQ OutQ  Up/Down State  PfxRcd PfxAcc
10.30.31.3       4  65200   8091068   7454502    0    0  170d15h Estab  48     48
10.30.47.2       4  65200   7467159   7454575    0    0  862d16h Estab  46     46
10.30.94.34      4  65202   4765404   3668243    0    0   13d16h Estab  5      6
'''
    parser = CliParser(attributes=attributes_2)
    result_2 = parser.parse_cli(data=data_2)

    diff_config = {'grouping' :['ROUTER_ID', 'LOCAL_AS', 'BGP_NEIGH', 'NEIGH_AS'],
             'index' :['ROUTER_ID', 'LOCAL_AS', 'BGP_NEIGH', 'NEIGH_AS'],
             'check' :['STATE_PFXRCD', 'STATE_PFXACC'],
            }
    diff = DiffTable.diff_generic(result_1, result_2, diff_config)
    pprint.pprint(diff)
