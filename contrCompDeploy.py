import subprocess
import os  # 文件读写
import shutil  # 文件复制、移动
import re  # 正则表达式
import json  # json
from typing import List, Set

import _pysha3  # 安装pysha3后导入
from contrbin import ContractDisasm  # 合约反汇编代码处理

# 文件夹路径结尾须加”/"
truffle_project_path = '/home/hhy/trufflePro/'  # truffle项目目录
tmp_sol_dir_path = '/home/hhy/Desktop/sol/'  # 暂存合约源文件目录
tmp_migration_dir_path = truffle_project_path + 'tmp_migrations/'  # 合约部署文件暂存目录
abi_dir_path = truffle_project_path + 'abis/'  # abi文件存放目录
bin_dir_path = truffle_project_path + 'bins/'  # bin文件存放目录
abi_sig_dir_path = truffle_project_path + 'abi_sigs/'  # abi签名文件存放目录
bin_sig_dir_path = truffle_project_path + 'bin_sigs/'  # bin签名文件存放目录
addrmap_file_path = truffle_project_path + 'addrmap.csv'  # 合约地址文件
runtime_bin_dir_path = truffle_project_path + 'runtime_bins/'  # runtime字节码文件存放目录

contract_min_version = 4  # 合约最老大版本
contract_max_version = 6  # 合约最新大版本
default_contract_version = '0.4.18'  # 默认合约版本
compile_version_list = ['0.1.7', '0.2.2', '0.3.6', '0.4.26', '0.5.17', '0.6.11']  # 大版本对应编译器合约版本
contract_deploying_group_size = 6  # 1组待部署合约的合约数


def main():
    if not contracts_compile():
        return
    get_ABIs_and_BINs()
    get_ABI_sigs()
    get_BIN_sigs()
    create_deploy_files()
    contracts_deploy()
    pass


def handle_path_same_name(src_path: str, dest_path: str):
    """
    处理同名文档，将原同名文档重命名
    :param src_path: 原重名文件路径
    :type src_path: str
    :param dest_path: 修改后文件路径
    :type dest_path: str
    """
    if os.path.exists(src_path):
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        os.rename(src_path, dest_path)


def make_dir(path: str):
    """
    新建文件夹
    :param path:文件夹路径
    :type path: str
    """
    if not os.path.exists(path):
        os.mkdir(path)


def remove_dir(path: str):
    """
    删除文件夹
    :param path: 文件夹路径
    :type path: str
    """
    if os.path.exists(path):
        shutil.rmtree(path)


def get_sol_version(file_path: str):
    """
    获取合约文件的版本号
    :param file_path:合约文件路径
    :type file_path: str
    :returns version，versionStr:
        version：string 合约大版本
        versionStr：string 合约具体版本字符串
    """
    with open(file_path) as fo:
        # while True:
        for line in fo:
            version_line = re.search(r'^pragma\s+solidity\s+(\^|>=)(0.(\d)+.\d+)[\s;]', line)
            if version_line:
                return version_line.group(3), version_line.group(2)
        return default_contract_version.split('.')[1], default_contract_version


def contracts_compile() -> bool:
    """
    编译合约
    :return 合约编译过程中是否有出错，出错返回False
    """
    # 创建对应大版本合约文件夹
    comp_dir_path = truffle_project_path + 'contracts'
    handle_path_same_name(comp_dir_path, comp_dir_path + '0')  # 防止编译文件夹重名
    for i in range(contract_min_version, contract_max_version + 1):
        remove_dir(comp_dir_path + f'_{i}')
        make_dir(comp_dir_path + f'_{i}')

    # 获取版本信息并将合约移入对应大版本文件夹
    files = os.listdir(tmp_sol_dir_path)
    for file_name in files:
        file_path = tmp_sol_dir_path + file_name
        if os.path.isfile(file_path):
            version_set = get_sol_version(file_path)
            # print(versionSet[0])
            shutil.copy(file_path, comp_dir_path + '_' + version_set[0])
    print('Preparation before compilation is done.')

    # 对每个大版本合约分别编译
    comp_flag = True
    for i in range(contract_min_version, contract_max_version + 1):
        contract_dir_path = comp_dir_path + f'_{i}'
        os.rename(contract_dir_path, comp_dir_path)
        set_compile_version(compile_version_list[i - 1])  # 设置Truffle合约编译器版本
        if contracts_compile_by_truffle():  # 编译合约
            print(f'Version {i} contracts compiled successfully.')
        else:
            comp_flag = False
            print(f'Version {i} contracts compiled failed.')
        os.rename(comp_dir_path, contract_dir_path)
    print('Compilation is done!\n')
    if not comp_flag:
        for i in range(contract_min_version, contract_max_version + 1):
            shutil.rmtree(comp_dir_path + f'_{i}')  # 用于将contracts_X目录删除*
    return comp_flag


def contracts_compile_by_truffle() -> bool:
    """
    对每个大版本版本的合约进行编译
    :return 编译是否成功
    """
    os.chdir(truffle_project_path + 'contracts')
    if not os.listdir(os.curdir):  # 若编译文件夹为空则返回
        return True

    # 使用Truffle进行编译
    compile_info = subprocess.getstatusoutput('truffle compile')
    # print(compileInfo)
    if compile_info[0] == 0:  # 编译成功
        return True
    else:
        print(compile_info[1])  # 编译失败输出编译信息
        return False


def get_contract_build_info(dir_path: str, file_name: str) -> dict:
    """
    获取Truffle编译合约后的json文件信息
    :param dir_path: json文件目录
    :type dir_path: str
    :param file_name: 合约文件名
    :type file_name: str
    :return: 编译后的信息json对象
    :rtype: dict
    """
    with open(dir_path + file_name) as rfo:
        return json.load(rfo)


def get_contract_ABI(build_info: dict):
    """
    从编译信息中获取合约ABI文件
    :param build_info: 合约编译信息
    :type build_info: dict
    """
    file_name = build_info['contractName'] + '.abi'
    with open(abi_dir_path + file_name, 'w') as wfo:
        json.dump(build_info['abi'], wfo)


def get_contract_BIN(build_info: dict):
    """
    从编译信息中获取合约的BIN文件（runtime字节码）
    :param build_info: 合约编译信息
    :type build_info: dict
    """
    file_name = build_info['contractName'] + '.bin'
    with open(bin_dir_path + file_name, 'w') as wfo:
        tmp = build_info['deployedBytecode'].lstrip('0x')
        wfo.write(tmp)


def get_contract_runtime_BIN(build_info: dict):
    file_name = build_info['contractName'] + '.evm'
    with open(runtime_bin_dir_path + file_name, 'w') as wfo:
        wfo.write(build_info['deployedBytecode'])


def get_ABIs_and_BINs():
    """获取合约的ABI和BIN"""
    build_dir_path = truffle_project_path + 'build/contracts/'
    # 创建存放目录
    make_dir(abi_dir_path)
    make_dir(bin_dir_path)
    # make_dir(runtime_bin_dir_path)

    # 遍历合约编译后的文件提取ABI和BIN
    files = os.listdir(build_dir_path)
    for file_name in files:
        file_path = build_dir_path + file_name
        if os.path.isfile(file_path):
            try:
                build_info = get_contract_build_info(build_dir_path, file_name)
                get_contract_ABI(build_info)
                get_contract_BIN(build_info)
                # get_contract_runtime_BIN(build_info)
            except:
                continue
    print("Got contracts' ABIs and BINs!\n")


def set_compile_version(version_str: str):
    """
    设置truffle-config.js文件中的solc版本
    :param version_str：需要设定的版本
    :type version_str: str
    """
    config_file = truffle_project_path + 'truffle-config.js'
    tmp_config_file = truffle_project_path + '.truffle-config.js.bak'
    with open(config_file) as rfo, open(tmp_config_file, 'w') as wfo:
        for line in rfo:
            wfo.write(re.sub(r'(?<=\s)version: "0.(\d)+.\d+"', f'version: "{version_str}"', line))
    os.remove(config_file)
    os.rename(tmp_config_file, config_file)
    print(f'Truffle compiled version is set to {version_str}')


def check_contract_constructor(file_name: str) -> List[dict]:
    """
    检查合约的构造函数， 若需要输入参数则进行输入
    :param file_name: 合约文件名
    :type file_name: str
    :return: inputs：构造函数输入的对象列表
    :rtype: list[dict]
    """
    # 打开合约对应ABI文件
    file_name = file_name.replace('.sol', '.abi')
    try:
        with open(abi_dir_path + file_name) as fo:
            abi = json.load(fo)
    except FileNotFoundError:
        print(f"Can't find ABI file of {file_name}")
        return None

    inputs = []
    for elem in abi:
        if 'type' in elem and elem['type'] == 'constructor':
            if 'inputs' in elem and elem['inputs']:  # 判断合约有无构造函数且须参数输入
                inputs = elem['inputs']
            break
    if not inputs:
        return None
    # 进行参数输入
    print('Please input contract Constructor Parameters:')
    for ipt in inputs:
        ipt['value'] = input(f'Param:{ipt["name"]}, Type:{ipt["type"]}, Value: ')
    return inputs


def create_deploy_files():
    """创建Truffle部署合约所需的合约部署文件"""
    # 创建合约部署文件暂存目录
    remove_dir(tmp_migration_dir_path)
    make_dir(tmp_migration_dir_path)

    no = 0
    mig_group_dir_path = ''
    # 遍历每个合约暂存文件夹，生成合约部署文件，并按照contract_deploying_group_size数目为一组进行分组
    for version in range(contract_min_version, contract_max_version + 1):
        contract_dir_path = truffle_project_path + f'contracts_{version}'
        contracts_list = os.listdir(contract_dir_path)
        for sol_name in contracts_list:
            if no % contract_deploying_group_size == 0:
                mig_group_dir_path = tmp_migration_dir_path + f'group_{no // contract_deploying_group_size}/'
                os.mkdir(mig_group_dir_path)

            deploy_info = 'Contract'
            ipt = check_contract_constructor(sol_name)
            if ipt:  # 合约构造函数须参数添加
                for i in range(len(ipt)):
                    deploy_info += f",{ipt[i]['value']}"

            file_content_lists = [f'var Contract = artifacts.require("{sol_name}");\n',
                                  'module.exports = function(deployer) {\n',
                                  f'\tdeployer.deploy({deploy_info});\n', '};']
            with open(mig_group_dir_path + f'{no + 1}_{sol_name}.js', 'w') as fo:
                fo.writelines(file_content_lists)
            no += 1

    print("Create deploy files successfully!\n")


def contracts_deploy():
    """部署合约到区块链"""
    # 处理原”migrations“文件，防止重名
    migration_dir_path = truffle_project_path + 'migrations/'
    handle_path_same_name(migration_dir_path, truffle_project_path + 'migrations0/')

    # 以组为单位批量部署合约
    os.chdir(truffle_project_path)
    addr_map = {}
    mig_group_dir_list = os.listdir(tmp_migration_dir_path)
    mig_group_dir_list.sort(key=lambda self: int(self.lstrip('group_')))  # 对文件夹排序
    for mig_group_dir_name in mig_group_dir_list:
        mig_group_dir_path = tmp_migration_dir_path + mig_group_dir_name
        shutil.copytree(mig_group_dir_path, migration_dir_path)
        print(f'Start deploying contracts in {mig_group_dir_name}...')
        deploy_info = subprocess.getstatusoutput('truffle migrate --reset')

        if deploy_info[0] == 0:  # 部署成功
            print(f'Deploy contracts in {mig_group_dir_name} successfully!')
            # shutil.rmtree(mig_group_dir_path)  # 用于将合约部署文件暂存目录删除*
        else:  # 部署失败输出部署信息
            print(f'Deploy contracts in {mig_group_dir_name} failed!')
            print(deploy_info[1])
            # 提取部署合约的合约名和合约地址
        re_str = r"(((Replacing)|(Deploying))\s'(.+)(?='))|> contract address:\s+(0x\w+)|(Error:)"
        result = re.findall(re_str, deploy_info[1])
        i = 0
        try:
            while i < len(result):
                if result[i + 1][6] == '':
                    addr_map[result[i][4]] = result[i + 1][5]
                i += 2
        except IndexError:
            print('Deploying has an error.')
        print(addr_map)

        shutil.rmtree(migration_dir_path)
    print('Deployment is done!')
    print(f'Deployed {len(addr_map)} contracts.')

    # 创建合约名-合约地址文件
    if addr_map:
        with open(addrmap_file_path, 'w') as fo:
            for name, address in addr_map.items():
                fo.write(f'{address},\t{name}\n')
        print("Contracts' addresses have been saved!\n")


def get_funcs(abi: dict) -> List[dict]:
    """
    获取函数
    :param abi: 该合约abi的json对象
    :type abi: dict
    :return func_list: 该合约的函数对象列表
    :rtype: list[dict]
    """
    func_list = []
    for elem in abi:
        if 'type' in elem and elem['type'] == 'function':
            func_list.append(elem)
    return func_list


def get_func_sig(func: dict):
    """
    获取函数签名
    :param func: 函数对象
    :type func: dict
    :return: 函数签名
    :rtype: str
    """
    if "name" not in func:
        return None
    name = func['name']
    if 'inputs' not in func:
        return name + '()'
    else:
        inputs = func['inputs']
        types = []
        for ipt in inputs:
            types.append(ipt['type'])
        types_str = ','.join(types)
        return name + '(' + types_str + ')'


def get_func_sig_hash(sig: str) -> str:
    """
    获取函数签名的hash值，即函数选择器
    :param sig: 函数签名
    :type sig: str
    :return bytes4：函数选择器
    :rtype: str
    """
    s = _pysha3.keccak_256()
    s.update(sig.encode('utf8'))
    hex_sig = s.hexdigest()
    bytes4 = '0x' + hex_sig[:8]  # hash值前4字节
    return bytes4


def get_contract_ABI_sig(dir_path: str, file_name: str):
    """
    单个文件获取函数选择器
    :param dir_path: 合约ABI文件夹路径
    :type dir_path: str
    :param file_name: 合约ABI文件名
    :type file_name: str
    """
    with open(dir_path + file_name) as rfo:
        abi_info = json.load(rfo)
        if abi_info:
            func_list = get_funcs(abi_info)  # 获取合约的函数列表
            if func_list:
                wfo = open(abi_sig_dir_path + file_name + '.sig', 'w')
                for func in func_list:
                    sig = get_func_sig(func)  # 获取函数签名
                    if sig:
                        sig_hash = get_func_sig_hash(sig)  # hash处理函数签名获取函数选择器
                        wfo.write(f'{sig_hash}:{sig}\n')
                wfo.close()


def get_ABI_sigs():
    """
    获取合约的ABI签名"""
    make_dir(abi_sig_dir_path)
    abi_dir_list = os.listdir(abi_dir_path)
    for abi_file_name in abi_dir_list:
        try:
            get_contract_ABI_sig(abi_dir_path, abi_file_name)
        except:
            continue
    print("Got contracts' ABI signatures!\n")


def get_BIN_sigs():
    """获取合约的BIN签名"""
    make_dir(bin_sig_dir_path)
    bin_dir_list = os.listdir(bin_dir_path)
    for bin_file_name in bin_dir_list:
        # print(bin_file_name)
        if os.path.isfile(bin_dir_path + bin_file_name):
            try:
                get_contract_BIN_sig(bin_dir_path, bin_file_name)
            except:
                continue
    print("Got contracts' BIN signatures!\n")


def save_func_disasm_codes(func_sig: str, func_codes: List[List[str]]):
    """
    存储分段后的函数反汇编代码
    :param func_sig: 函数签名
    :type func_sig: str
    :param func_codes: 函数代码列表
    :type func_codes: list[list[str]]
    """
    with open(bin_sig_dir_path + func_sig + '.asm', 'w') as wfo:
        for code in func_codes:
            for c in code:
                wfo.write(f'{c}\n')
            wfo.write('\n\n')


def has_CALL_opcode(func_codes: List[List[str]], i: int) -> bool:
    """
    判断函数第i段代码是否含有CALL字节码
    :param func_codes: 函数代码列表
    :type func_codes: list[list[str]]
    :param i: 代码段的序号
    :type i: int
    :return: 是否含有CALL
    """
    for code in func_codes[i]:
        if code == 'CALL':
            return True
    return False


def get_extern_call_sigs_from_codes(func_codes: List[List[str]]) -> Set[str]:
    """
    获取函数的外部调用函数选择器
    :param func_codes: 函数代码列表
    :type func_codes: list[list[str]]
    :return: 外部调用函数的选择器集合
    """
    extern_call_sigs = set()
    for i in range(len(func_codes)):
        for code in func_codes[i]:
            # 当前代码段有函数选择器， 且下一个代码段有CALL指令
            if code.startswith('PUSH4 ') and code.split()[1] != '0xffffffff' and has_CALL_opcode(func_codes, i + 1):
                extern_call_sigs.add(code.split()[1])
    return extern_call_sigs


def get_contract_BIN_sig(dir_path: str, file_name: str):
    """
    获取单个合约的二进制签名
    :param dir_path: 合约BIN文件夹路径
    :type dir_path: str
    :param file_name: 合约BIN文件名
    :type file_name: str
    """
    cds = ContractDisasm()  # 构建反汇编对象
    cds.get_runtime_data(dir_path + file_name)
    func_sigs = cds.get_func_sigs()
    bin_sigs_dict = {}
    for func in func_sigs:
        func_codes = cds.get_func_codes(func[1])
        # save_func_disasm_codes(func[0], func_codes)
        extern_call_sig = get_extern_call_sigs_from_codes(func_codes)
        if extern_call_sig:
            bin_sigs_dict[func[0]] = extern_call_sig
    # 将合约BIN签名写入文件
    if bin_sigs_dict:
        with open(bin_sig_dir_path + file_name + '.sig', 'w') as fo:
            for func_sig in bin_sigs_dict.keys():
                # print(func_sig, ':', bin_sigs_dict[func_sig])
                fo.write(func_sig + ':' + ' '.join(bin_sigs_dict[func_sig]) + '\n')


if __name__ == '__main__':
    main()
