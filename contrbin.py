import subprocess


class ContractDisasm:
    def __init__(self):
        self.__runtime_code_lines = []  # runtime部分反汇编代码
        self.__jump_table = {}  # 地址号int-代码行号的映射
        self.__jump_line_no_set = set()   # 合约函数中的全部跳转行号

    def get_runtime_data(self, file_path):
        """
        获取runtime字节码反汇编后数据
        :param file_path: runtime字节码文件路径
        :type file_path: str
        """
        # 反汇编
        err, runtime_data_lines = subprocess.getstatusoutput(f'evm disasm {file_path}')
        runtime_data_lines = runtime_data_lines.split('\n')
        if err:
            runtime_data_lines.pop()    # 去除错误行
        #     print('ERROR:', runtime_data_lines.pop())  # 有错误提示*
        if not runtime_data_lines[0].startswith('000000'):
            runtime_data_lines.pop(0)
        for i in range(len(runtime_data_lines)):
            data = runtime_data_lines[i].split(':')
            self.__runtime_code_lines.append(data[1].strip())     # 添加代码部分
            self.__jump_table[int(data[0])] = i       # 添加跳转字典

    def get_func_sigs(self):
        """
        获取合约的函数选择器列表
        :return: func_sigs list(set): 合约签名列表，元素为二元组包括：函数选择器和函数入口地址
        """
        func_sigs = []
        for line_no in range(len(self.__runtime_code_lines)):
            if self.__runtime_code_lines[line_no] == 'STOP':
                break
            if self.__runtime_code_lines[line_no].startswith('PUSH4 ') and \
                    self.__runtime_code_lines[line_no + 1] == 'EQ':
                func_sigs.append(
                    [self.__runtime_code_lines[line_no].split()[1],
                     int(self.__runtime_code_lines[line_no + 2].split()[1], 16)])
        return func_sigs

    def __is_func_ending(self, line_no):
        """
        函数是否终止
        :param line_no: 待判断的代码行号
        :type line_no: int
        :return: 是否终止
        """
        if self.__runtime_code_lines[line_no] == 'Missing opcode 0xfd' \
                or self.__runtime_code_lines[line_no] == 'Missing opcode 0xfe' \
                or self.__runtime_code_lines[line_no] == 'RETURN' \
                or self.__runtime_code_lines[line_no] == 'STOP':
            return True
        return False

    def __get_seg_addr_line_no(self, line_no):
        """
        获取当前行代码段地址对应的行号
        :param line_no: 待判断的代码行号
        :return: 行号
        :rtype: int
        """
        addr = int(self.__runtime_code_lines[line_no].split()[1], 16)
        if addr in self.__jump_table:
            return self.__jump_table[addr]
        return 0

    def __is_func_jump_addr(self, line_no):
        """
        是否是跳转地址代码，即代码中包含代码段地址入口
        :param line_no: 待判断的代码行号
        :type line_no: int
        :return: 是否是跳转地址代码
        """
        if self.__runtime_code_lines[line_no].startswith('PUSH2 '):
            if self.__runtime_code_lines[line_no + 1] == 'JUMPI' or self.__runtime_code_lines[line_no + 1] == 'JUMP':
                return True
            elif self.__runtime_code_lines[self.__get_seg_addr_line_no(line_no)] == 'JUMPDEST':
                return True
        return False

    def get_seg_codes(self, start_line_no):
        """
        获取由该代码段可达的所有代码段
        :param start_line_no: 代码段起始行号
        :type start_line_no: int
        :return: 该代码段可达的所有代码段的列表
        """
        end_line_no = start_line_no + 1     # 代码段结束行号
        func_code_list = []     # 代码段列表
        jump_line_no_set = set()    # 改代码段包含的跳转行号的集合
        while end_line_no < len(self.__runtime_code_lines):   # 未到结尾
            # 判断该代码段是否到结尾，到结尾则退出循环
            if self.__is_func_ending(end_line_no) or self.__runtime_code_lines[end_line_no+1] == 'JUMPDEST':
                break
            # 判断代码是否是跳转代码，且其跳转到的行号未出现过
            if self.__is_func_jump_addr(end_line_no) and end_line_no not in self.__jump_line_no_set:
                jump_line_no = self.__get_seg_addr_line_no(end_line_no)   # 获取跳转的行号
                jump_line_no_set.add(jump_line_no)  # 添加该代码段跳转行号集合
                self.__jump_line_no_set.add(jump_line_no)     # 添加到全部代码段跳转行号集合
            end_line_no += 1
        # 添加当前代码段列表
        func_code_list.append(self.__runtime_code_lines[start_line_no:end_line_no + 1])
        # print(start_line_no)
        # print(func_code_list)
        # 遍历该代码段包含的所有跳转行号， 获取其下代码段
        for jump_line_no in jump_line_no_set:
            func_code_list.extend(self.get_seg_codes(jump_line_no))
        return func_code_list

    def get_func_codes(self, func_addr):
        """
        获取函数包含的所有代码段列表
        :param func_addr: 函数入口地址
        :type func_addr: int
        :return: func_codes 函数代码段列表
        """
        self.__jump_line_no_set.clear()
        func_start_line_no = self.__jump_table[func_addr]     # 函数起始行号：函数入口地址对应的行号
        return self.get_seg_codes(func_start_line_no)   # 解析函数里所有代码段
