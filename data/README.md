# data

存放一些需要使用的文件（文件基本来自ctest：https://github.com/xlab-uiuc/openctest）

## 目录介绍

1. ctest_mapping : ctest的配置项和单元测试映射关系（json）。
2. default_configs : 被测项目的默认配置。
3. deprecated_configs : 被测项目中的被遗弃的配置项和新的配置项。
4. test_rewrite : 重写的ctest补丁。

## 文件介绍

1. setup_ubuntu.sh : 为ubuntu系统下载一些必须的软件。
2. add_project.sh : 添加被测项目。

## 使用说明
1. 首先可以运行setup_ubuntu.sh 安装一些软件
2. 使用add_project.sh 添加被测项目（后面需要添加参数，根据里面的main函数添加）
3. 如果需要可以把test_rewrite里面的补丁打入到test中，这里是重写的单元测试。