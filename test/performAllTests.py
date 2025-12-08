import os
import re
import sys
import unittest
from os.path import dirname, abspath, join

ROOT_DIR = dirname(dirname(abspath(__file__)))
SRC_DIR = join(ROOT_DIR, "src")
DATA_DIR = join(ROOT_DIR, "data")
TEST_DIR = join(ROOT_DIR, "test")

sys.path.append(SRC_DIR)
sys.path.append(DATA_DIR)
sys.path.append(TEST_DIR)


def testAllInDir():  # sourcery skip: low-code-quality
    """
    Look at the target directory and search & perform all tests in it.
    """
    prefix = "*" * 70 + "\n" + "*" * 20 + " "
    suffix = "\n" + "*" * 70
    suffixLine = '-' * 70

    testCount = 0
    failCount = 0
    skipCount = 0
    failedList = []

    current_path = os.path.dirname(os.path.abspath(__file__))  # 获取当前目录路径

    for root, dirs, files in os.walk(current_path):
        # 扫描测试所有的下级目录
        for _dir in dirs:
            if '_' in _dir or '-' in _dir or _dir.startswith("defaultXml"):
                continue

            print(f'{prefix}now look at {_dir}{suffix}', file=sys.stderr)

            """
            自动搜索该目录下所有的test*.py文件, 默认包含目录下所有文件里面的所有方法。
            目录
               -文件(s)
                   -类(s)
                      -方法(s)
            """
            loader = unittest.TestLoader()
            start_path = os.path.join(current_path, _dir)
            dirSuit = loader.discover(start_path, pattern="test*.py", top_level_dir=start_path)
            for fileSuit in dirSuit:  # 下降至文件层
                for classSuit in fileSuit:  # 下降至类层
                    # 获取文件名 test*.py
                    match = re.compile(r'(test\w+)\.\w+\s').findall(classSuit.__str__())
                    if match.__len__() == 0:
                        print(f"{suffixLine}\nSkip one class suit!!!", file=sys.stderr)
                        skipCount += 1
                        continue
                    else:
                        fileName = match[0]
                    print(f"{suffixLine}\n{fileName}.py contains {classSuit.countTestCases()} testcases:",
                          file=sys.stderr)
                    """
                    方法层粒度测试
                    """
                    with open(f"{os.path.join(start_path, fileName)}.log", "w") as log:
                        sys.stdout = log
                        for methodTest in classSuit._tests:  # 下降至方法层
                            runner = unittest.TextTestRunner(stream=log, verbosity=3)
                            match = re.compile('(test[\w]+)\s').findall(methodTest.__str__())
                            methodName = match[0]
                            print(f"\t{methodName}...", end='', file=sys.stderr)
                            print(f"{prefix}{methodName}{suffix}")
                            # 获取单个方法层的测试样例并运行
                            singleSuit = unittest.TestSuite([methodTest])
                            result = runner.run(singleSuit)
                            # 统计测试数量和失败数量
                            testCount += 1
                            failCount += len(result.errors)

                            if result.errors:
                                print("failed.", file=sys.stderr)
                                failedList.append(f"{_dir}/{fileName}.py:{methodName}")
                            else:
                                print("ok.", file=sys.stderr)

    sys.stdout = sys.__stdout__
    passedCount = testCount - failCount
    print(
        f"\n测试通过率{100 * passedCount / testCount:.2f}%({passedCount}/{testCount}, "
        f"{failCount} failed, {skipCount} files skipped)")

    if failCount > 0:
        print("失败的单元测试：")
        for ut in failedList:
            print(f"\t{ut}")


if __name__ == "__main__":
    testAllInDir()
    print("更多信息，请查看日志.")
