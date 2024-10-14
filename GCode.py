#!/usr/bin/env micropython
"""
功能：完成对Gcode文件的解析，提取出XYZ等操作
版本：V1.0
日期：2023年3月14日
作者：王铭东
网站：www.itprojects.cn
"""


import re
import time


class GCodeParse:
    re_rules = [
        ('([GXYZ]\+?-?\d+\.?\d*)[ ]*([XYZF]\+?-?\d+\.?\d*)[ ]*([XYZF]\+?-?\d+\.?\d*)[ ]*([XYZF]\+?-?\d+\.?\d*)', 4),
        ('([GXYZ]\+?-?\d+\.?\d*)[ ]*([XYZF]\+?-?\d+\.?\d*)[ ]*([XYZF]\+?-?\d+\.?\d*)', 3),
        ('([GXYZ]\+?-?\d+\.?\d*)[ ]*([XYZF]\+?-?\d+\.?\d*)', 2),
        ('([GXYZ]\+?-?\d+\.?\d*)', 1),
        ('([S]\+?-?\d+\.?\d*)', 1),
    ]

    def __init__(self, file_path):
        self.x = 0
        self.y = 0
        self.z = 0
        self.g = 0
        self.crules = []
        for rule, num in self.re_rules:
            self.crules.append((re.compile(rule), num))
        # 存储文件对象
        self.gcode_file = open(file_path, "r")

    def __del__(self):
        try:
            self.gcode_file.close()
        except Exception as ret:
            pass

    def read_one_line(self):
        """
        读1行gcode文件内容
        """
        text_line = self.gcode_file.readline()
        if text_line:
            return self.parse_one_line(text_line)
        else:
            return None  # 表示已读取完

    def parse_one_line(self, text_line):
        """
        对读取到的一行.gcode文件代码进行处理
        """
        xyz_update = 0  # 0表示未更新，1表示更新
        text_line = text_line.strip()
        for rule, num in self.crules:
            ret = rule.search(text_line)
            if ret:
                ret_dict = dict()
                for i in range(1, num+1):
                    word = ret.group(i)
                    if word:
                        digt = float(word[1:])
                        # print(digt)
                        key = word[0]
                        if 'X' == key:
                            ret_dict['x'] = digt
                        elif 'Y' == key:
                            ret_dict['y'] = digt
                        elif 'Z' == key:
                            ret_dict['z'] = digt
                        elif 'G' == key:
                            ret_dict['g'] = digt
                        elif 'S' == key:
                            ret_dict['s'] = digt
                return ret_dict
        return {}

'''
if __name__ == '__main__':
    # 1. 创建Gcode解析 对象，参数是 要解析的.gcode文件
    gcode_obj = GCodeParse("test.gcode")
    # 2. 读取1行.gcode文件的代码
    gcode_dict = gcode_obj.read_one_line()
    while gcode_dict is not None:
        print("提取出的xyzgs>>", gcode_dict)
        time.sleep(0.1)
        gcode_dict = gcode_obj.read_one_line()
'''