import os.path
import sys
import time
import unittest
import warnings

sys.path.append("../../src")

from testValidator.CEITSystemTester import CEITSystemTester
from testValidator.SystemTester import SystemTester
from dataModel.Testcase import Testcase
from dataModel.TestResult import TestResult
from utils.Configuration import Configuration
from utils.ShowStats import ShowStats

class TestCEITST(unittest.TestCase):

    # @classmethod
    # def setUpClass(cls) -> None:
    #     warnings.simplefilter('ignore', ResourceWarning)
    @classmethod
    def setUpClass(cls) -> None:
        print("start to test class `CEITSystemTester`")
        Configuration.parseConfiguration()
        ShowStats.fuzzerStartTime = time.time()
        ShowStats.runTime = 99999.99
        warnings.simplefilter('ignore', ResourceWarning)

    def test_runTest(self) -> TestResult:
        testcase = Testcase()
        curDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        testcase.filePath = os.path.join(curDir, Configuration.putConf['test_st_conf_path'])
        print(f"testcase file path is : {testcase.filePath}")
        return CEITSystemTester().runTest(testcase=testcase)

if __name__ == "__main__":
    unittest.main()