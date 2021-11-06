# Contracts-Compile-And-Deploy
以太坊智能合约编译及签名信息提取脚本  
## 主要功能
* 基于 Truffle 框架的智能合约 `.sol` 文件的自动化编译(以 Solidity 的大版本分别编译)
* 提取智能合约的 ABI 和字节码
* 提取智能合约的 ABI 签名
* 根据字节码提取智能合约的 BIN 签名(外部调用函数签名)
* 基于 Truffle 框架的智能合约自动化部署上链
## 使用方法
1. 安装 Truffle 框架并构建一个项目目录
2. 删除创建的 Truffle 项目目录下除 `truffle-config.js` 以外的文件夹和文件
3. 设置 Truffle 连接的以太坊私有链
4. 打开用于部署合约的私有链, 解锁账户后进行挖矿
5. 根据运行环境修改脚本 `contrCompDeploy.py` 中的路径等参数
6. 运行脚本 `contrCompDeploy.py` 
* 具体参考: [智能合约模糊测试编译部署脚本_LostUnravel的博客 - 掘金](https://juejin.cn/post/7027462095511748615/)
