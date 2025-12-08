import copy
import random
import sys
import unittest

from utils.ConfAnalyzer import ConfAnalyzer
from utils.Configuration import Configuration

sys.path.append("../../src")

from dataModel.ConfItem import ConfItem
from dataModel.Testcase import Testcase
from testValidator.VirtualSystemTester import VirtualSystemTester
from testValidator.DichotomyTrimmer import DichotomyTrimmer


class testDichotomyTrimmer(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        Configuration.parseConfiguration()
        ConfAnalyzer.analyzeConfItems()

    def testDichotomyTrimmer(self) -> None:
        confItemIndexes = list(range(20))
        defaultValueMap = {f"ci{i}": "ok" for i in confItemIndexes}

        random.shuffle(confItemIndexes)

        # 构造脆弱性配置项集合
        vulnerableConfItemIndexes = confItemIndexes[:5]
        vulnerableConfItems: dict[str:list[str]] = {f"ci{i}": ["notok"] for i in vulnerableConfItemIndexes}

        # 构造待精简测试用例
        targetConfItemIndexes = confItemIndexes[:15]
        targetConfItems = []
        for i in targetConfItemIndexes:
            if i in vulnerableConfItemIndexes:
                targetConfItems.append(ConfItem(f"ci{i}", "str", "notok"))
            else:
                targetConfItems.append(ConfItem(f"ci{i}", "str", "ok"))
        random.shuffle(targetConfItems)
        testcase = Testcase(targetConfItems)

        # 基于脆弱性配置项集合创建一个虚拟系统测试器
        systemTester = VirtualSystemTester(vulnerableConfItems)

        # 生成一个精简器
        trimmer = DichotomyTrimmer(systemTester, defaultValueMap)

        print("Before Trimming:")
        print(testcase)

        testcase = trimmer.trimTestcase(copy.deepcopy(testcase))

        print("After Dichotomy Trimming:")
        print(testcase)

    def testDichotomyTrimmerBig(self) -> None:
        confItemIndexes = list(range(100))
        defaultValueMap = {f"ci{i}": "ok" for i in confItemIndexes}

        random.shuffle(confItemIndexes)

        # 构造脆弱性配置项集合
        vulnerableConfItemIndexes = confItemIndexes[:5]
        vulnerableConfItems: dict[str:list[str]] = {f"ci{i}": ["notok"] for i in vulnerableConfItemIndexes}

        # 构造待精简测试用例
        targetConfItemIndexes = confItemIndexes[:50]
        targetConfItems = []
        for i in targetConfItemIndexes:
            if i in vulnerableConfItemIndexes:
                targetConfItems.append(ConfItem(f"ci{i}", "str", "notok"))
            else:
                targetConfItems.append(ConfItem(f"ci{i}", "str", "ok"))
        random.shuffle(targetConfItems)
        testcase = Testcase(targetConfItems)

        # 基于脆弱性配置项集合创建一个虚拟系统测试器
        systemTester = VirtualSystemTester(vulnerableConfItems)

        # 生成一个精简器
        trimmer = DichotomyTrimmer(systemTester, defaultValueMap)

        print("Before Trimming:")
        print(testcase)

        testcase = trimmer.trimTestcase(copy.deepcopy(testcase))

        print("After Dichotomy Trimming:")
        print(testcase)


if __name__ == "__main__":
    unittest.main()
