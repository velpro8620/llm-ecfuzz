import os
import sys
import unittest
from os.path import dirname, abspath, join

import coverage

ROOT_DIR = dirname(dirname(abspath(__file__)))
SRC_DIR = join(ROOT_DIR, "src")
DATA_DIR = join(ROOT_DIR, "data")
TEST_DIR = join(ROOT_DIR, "test")

sys.path.append(SRC_DIR)
sys.path.append(DATA_DIR)
sys.path.append(TEST_DIR)

from utils.Configuration import Configuration

def testAllInDir():
    """
    全局覆盖率收集
    """
    prefix = "*" * 70 + "\n" + "*" * 20 + " "
    suffix = "\n" + "*" * 70
    current_path = os.path.dirname(os.path.abspath(__file__))  # 获取当前目录路径

    print(f"{prefix}now start to collect coverages{suffix}", file=sys.stderr)
    # 初始化coverage
    cov = coverage.coverage(cover_pylib=False,
                            branch=True,
                            include=f"*{os.path.sep}src{os.path.sep}*.py",
                            omit="*__init__.py")

    cov.start()
    covLog = open(os.path.join(current_path, "coverage.log"), "w")
    # 重定向标准输出
    sys.stdout = covLog
    sys.stderr = covLog
    # 生成一个新loader
    loader = unittest.TestLoader()
    # 生成一个新runner
    runner = unittest.TextTestRunner(stream=None, verbosity=0)
    suit = unittest.TestSuite()
    # 重复工作：找到所有tests
    for root, dirs, files in os.walk(current_path):
        for _dir in dirs:
            if '_' in _dir or '-' in _dir or _dir.startswith("defaultXml"):
                continue
            start_path = os.path.join(current_path, _dir)
            suit.addTest(loader.discover(start_path, pattern="test*.py", top_level_dir=start_path))
    # 运行
    runner.run(suit)
    cov.stop()
    cov.save()
    with open(os.path.join(current_path, 'coverage.txt'), 'w') as covFile:
        # 生成报告
        cov.report(show_missing=True, skip_empty=True, file=covFile)
        cov.html_report(directory=os.path.join(current_path, "coverage-html"))
    sys.stderr = sys.__stderr__


if __name__ == "__main__":
    Configuration.parseConfiguration()
    testAllInDir()
    print("覆盖率统计完毕.", file=sys.stderr)
