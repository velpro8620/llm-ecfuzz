import os.path
import sys
import time
import unittest

sys.path.append("../../src")

from testValidator.SystemTester import SystemTester
from dataModel.Testcase import Testcase
from dataModel.TestResult import TestResult
from utils.Configuration import Configuration
from utils.ShowStats import ShowStats
from testValidator.MonitorThread import MonitorThread
from queue import Queue

class TestST(unittest.TestCase):

    # @classmethod
    # def setUpClass(cls) -> None:
    #     warnings.simplefilter('ignore', ResourceWarning)
    @classmethod
    def setUpClass(cls) -> None:
        print("start to test class `SystemTester`")
        Configuration.parseConfiguration({})
        ShowStats.fuzzerStartTime = time.time()
        ShowStats.runTime = 99999.99

    def test_runTest(self) -> TestResult:
        testcase = Testcase()
        curDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        testcase.filePath = os.path.join(curDir, Configuration.putConf['test_st_conf_path'])
        print(f"testcase file path is : {testcase.filePath}")
        stop = Queue()
        res = SystemTester().runTest(testcase=testcase, stopSoon=stop)
        print(f"result status is : {res.status}")
        print(f"cpu exception is : {MonitorThread.CpuException}, memory exception is : {MonitorThread.MemoryException}, log file size exception is : {MonitorThread.FileSizeException}")
        return res

if __name__ == "__main__":
    unittest.main()