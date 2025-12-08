import os
import shutil
import stat
import sys, getopt
from time import time
import logging
from typing import Dict
import gc

from seedGenerator.SeedGenerator import SeedGenerator
from testValidator.TestValidator import TestValidator
from testcaseGenerator.TestcaseGenerator import TestcaseGenerator
from utils.ConfAnalyzer import ConfAnalyzer
from utils.Configuration import Configuration

from utils.InstanceCreator import InstanceCreator
from utils.Logger import Logger
from utils.ShowStats import ShowStats

import time, signal, threading

from queue import Queue

# ================= [新增导入开始] =================
from dotenv import load_dotenv
from analysis_agent import AnalysisAgent
from generate_agent import GenerateAgent
from RAG import get_vectorstore  # 导入 RAG 接口
from dataModel.Seed import Seed
from dataModel.ConfItem import ConfItem
# ================= [新增导入结束] =================

os.environ["TOKENIZERS_PARALLELISM"] = "false"

stopSoon = Queue()


class Fuzzer(object):
    def __init__(self):
        self.logger: logging.Logger = Logger.get_logger()
        self.logger.info("Initializing Fuzzer...")

        self.logger.info("Parse configurations...")
        self.commandConf: Dict[str, str] = self.getOpt()
        Configuration.parseConfiguration(self.commandConf)
        self.fuzzerConf: Dict[str, str] = Configuration.fuzzerConf
        self.putConf: Dict[str, str] = Configuration.putConf


        ShowStats.mutationStrategy = self.fuzzerConf['mutator'].split(".")[-1]
        # ShowStats.mutationStrategy = "SingleMutator"
        ShowStats.fuzzerStartTime = time.time()

        self.logger.info("Analyze PUT configurations...")
        ConfAnalyzer.analyzeConfItems()
        self.logger.info("Basic ConfItems :" + str(ConfAnalyzer.confItemsBasic))

        self.logger.info("Creating a SeedGenerator...")
        self.seedGenerator: SeedGenerator = SeedGenerator()

        # ================= [LLM & RAG 集成代码开始] =================
        self.logger.info(">>>>[LLM Integration] Starting LLM-based seed generation...")
        try:
            # 1. 加载环境变量
            load_dotenv()
            api_key = os.getenv("LLM_API_KEY")
            base_url = os.getenv("LLM_BASE_URL")
            model_name = os.getenv("LLM_MODEL_NAME")

            if api_key and base_url and model_name:
                # 2. [RAG] 加载向量数据库
                self.logger.info(">>>>[LLM Integration] Loading RAG vector store...")
                vector_store = get_vectorstore() # 获取向量库实例

                if vector_store:
                    self.logger.info(">>>>[LLM Integration] RAG store loaded. Agent will use retrieval.")
                else:
                    self.logger.warning(">>>>[LLM Integration] RAG store NOT found. Running without RAG.")

                # 3. 确定目标配置文件路径 (根据当前项目自动选择)
                current_project = self.fuzzerConf.get('project', 'hbase')
                # 定义项目到默认配置文件的映射关系
                project_mapping = {
                    'hadoop-hdfs': 'hdfs-default.xml',
                    'hadoop-common': 'core-default.xml',
                    'hbase': 'hbase-default.xml',
                    'zookeeper': 'zoo.cfg',
                    'alluxio': 'alluxio-site.properties'
                }
                config_filename = project_mapping.get(current_project, 'hbase-default.xml')

                # 拼接完整路径 (ECFuzz-main/data/default_conf_file/...)
                target_config_path = os.path.join(os.path.dirname(__file__), f"../data/default_conf_file/{config_filename}")

                if os.path.exists(target_config_path):
                    self.logger.info(f">>>>[LLM Integration] Target config file: {target_config_path}")
                    with open(target_config_path, "r", encoding="utf-8") as f:
                        config_content = f.read()

                    # 4. 实例化 Agent (注入 RAG vector_store)
                    # AnalysisAgent: 主要负责分析结构，通常不需要 RAG，但保持接口一致
                    analysis_agent = AnalysisAgent(
                        api_key=api_key,
                        base_url=base_url,
                        model_name=model_name
                    )

                    # GenerateAgent: 必须接收 vector_store 以启用 RAG 检索增强
                    generate_agent = GenerateAgent(
                        api_key=api_key,
                        base_url=base_url,
                        model_name=model_name,
                        vector_store=vector_store # <--- 传入向量库
                    )

                    # 5. 执行 LLM 流程
                    self.logger.info(">>>>[LLM Integration] Analyzing dependencies...")
                    deps_result = analysis_agent.analyze_config_dependencies(config_content)

                    self.logger.info(">>>>[LLM Integration] Generating seeds with RAG...")
                    
                    # [关键修复] 将种子数量从 5 改为 1
                    # HDFS 依赖过多，生成多个种子会导致 Token 溢出截断 JSON。
                    # 生成 1 个覆盖所有依赖的种子即可，后续变异交由 Fuzzer 处理。
                    seeds_result = generate_agent.generate_seeds(deps_result, num_seeds=1)

                    # 6. 将生成的 JSON 转为 ECFuzz 种子对象
                    generated_seeds_list = seeds_result.get("seeds", [])
                    self.logger.info(f">>>>[LLM Integration] Generated {len(generated_seeds_list)} seeds.")

                    for seed_data in generated_seeds_list:
                        conf_items = []
                        for param in seed_data.get("parameters", []):
                            p_name = param.get("name")
                            p_value = str(param.get("value"))

                            # 简单的类型推断，防止空类型
                            p_type = ConfAnalyzer.confItemTypeMap.get(p_name, "String")
                            conf_items.append(ConfItem(name=p_name, type=p_type, value=p_value))

                        if conf_items:
                            self.seedGenerator.addSeedToPool(Seed(confItems=conf_items))

                    self.logger.info(">>>>[LLM Integration] Custom seeds injected into pool.")
                else:
                    self.logger.warning(f">>>>[LLM Integration] Config file not found: {target_config_path}")
            else:
                self.logger.warning(">>>>[LLM Integration] Missing LLM env vars, skipping generation.")

        except Exception as e:
            import traceback
            print("\n========== LLM/RAG Error ==========")
            traceback.print_exc()
            print("===================================\n")
            self.logger.error(f">>>>[LLM Integration] Error: {e}")
        # ================= [LLM & RAG 集成代码结束] =================

        self.logger.info("Creating a TestcaseGenerator...")
        mutatorClassPath = self.fuzzerConf['mutator']
        self.testcaseGenerator: TestcaseGenerator = TestcaseGenerator(InstanceCreator.getInstance(mutatorClassPath))

        self.logger.info("Creating a TestValidator...")
        self.testValidator: TestValidator = TestValidator()
        if os.path.exists(self.fuzzerConf['plot_data_path']):
            os.remove(self.fuzzerConf['plot_data_path'])

        if self.fuzzerConf['data_viewer'] == 'True':
            from utils.DataViewer import DataViewer
            self.dataViewer = DataViewer(self.fuzzerConf['data_viewer_env'])

    def sigintHandler(self, signum, frame):
        stopSoon.put(True)
        self.logger.info(f">>>>[fuzzer] excludeConf : {ConfAnalyzer.excludeConf}; confMutationInfo : {ConfAnalyzer.confMutationInfo}")
        self.logger.info(f">>>>[fuzzer] receive SIGINT")
        time.sleep(1)
        exit(0)
        # process.kill()

    def deleteDir(self, directory):
        if os.path.exists( directory ):
            if not os.access(directory, os.W_OK):
                os.chmod(directory, stat.S_IWRITE)
            shutil.rmtree(directory)

    def getOpt(self) -> dict:
        ''' project, seed_pool_selection_ratio, seed_gen_seq_ratio, data_viewer, data_viewer_env,
        ctests_trim_sampling,ctests_trim_scale,skip_unit_test,force_system_testing_ratio
        host_ip,host_port,run_time(/h)
        '''
        argv = sys.argv[1:]
        res = {}
        try:
            opts, args = getopt.getopt(argv, "p",["project=","seed_pool_selection_ratio=","seed_gen_seq_ratio=","data_viewer=","data_viewer_env=","ctests_trim_sampling=","ctests_trim_scale=","skip_unit_test=","force_system_testing_ratio=","host_ip=","host_port=","run_time=","mutator=","systemtester=","ctest_total_time=","misconf_mode="])
            # opts, args = getopt.getopt(argv, ["project=","seed_pool_selection_ratio=","seed_gen_seq_ratio=","data_viewer=","data_viewer_env=","ctests_trim_sampling=","ctests_trim_scale=","skip_unit_test=","force_system_testing_ratio="])
        except:
            self.logger.info("Parameter Setting Error")
        for opt, arg in opts:
            if opt in ['--project']:
                res["project"] = arg
            elif opt in ['--seed_pool_selection_ratio']:
                res["seed_pool_selection_ratio"] = arg
            elif opt in ['--seed_gen_seq_ratio']:
                res["seed_gen_seq_ratio"] = arg
            elif opt in ['--data_viewer']:
                res["data_viewer"] = arg
            elif opt in ['--data_viewer_env']:
                res["data_viewer_env"] = arg
            elif opt in ['--ctests_trim_sampling']:
                res["ctests_trim_sampling"] = arg
            elif opt in ['--ctests_trim_scale']:
                res["ctests_trim_scale"] = arg
            elif opt in ['--skip_unit_test']:
                res["skip_unit_test"] = arg
            elif opt in ['--force_system_testing_ratio']:
                res["force_system_testing_ratio"] = arg
            elif opt in ['--host_ip']:
                res["host_ip"] = arg
            elif opt in ['--host_port']:
                res["host_port"] = arg
            elif opt in ['--run_time']:
                res["run_time"] = arg
            elif opt in ['--mutator']:
                res["mutator"] = arg
            elif opt in ['--systemtester']:
                res["systemtester"] = arg
            elif opt in ['--ctest_total_time']:
                res["ctest_total_time"] = arg
            elif opt in ['--misconf_mode']:
                res["misconf_mode"] = arg
        return res

    def run(self):
        """
        The run function is the main function of the fuzzer. It is responsible for
        looping through all the test cases and running them against a target. The
        fuzzer will run each test case in order, one after another, until it has reached
        the end of its list, or it has reached a maximum number of loops (if specified).
        """
        # firstly, delete execs
        self.testValidator.getCov.delete_execs()
        if self.fuzzerConf['data_viewer'] == 'True':
            from utils.DataViewer import startDrawing
            startDrawing(self.dataViewer)

        ShowStats.initPlotData()
        ShowStats.writeToPlotData()

        signal.signal(signal.SIGINT, self.sigintHandler)
        t1 = threading.Thread(target=ShowStats.run, args=[stopSoon])
        t1.start()
        fuzzingLoop = int(self.fuzzerConf['fuzzing_loop'])

        self.deleteDir(Configuration.fuzzerConf['unit_testcase_dir'])
        self.deleteDir(Configuration.fuzzerConf['unit_test_results_dir'])
        self.deleteDir(Configuration.fuzzerConf['sys_test_results_dir'])
        self.deleteDir(Configuration.fuzzerConf['sys_testcase_fail_dir'])

        # print("\033[37m")
        if fuzzingLoop > 0:
            self.logger.info(f"Fuzzer ready to run for {fuzzingLoop} loops...")
            for _ in range(fuzzingLoop):
                try:
                    if (not stopSoon.empty()):
                        t1.join()
                        break
                except Exception as e:
                    print(e)
                    break
                try:
                    self.loop(stopSoon)
                except Exception as e:
                    import traceback
                    print("\n========== Fuzzer Loop Crash ==========")
                    traceback.print_exc()
                    print("=======================================\n")
                    self.logger.info(e)
                    break
        else:
            self.logger.info("Fuzzer ready to run forever...")
            while True:
                try:
                    if not stopSoon.empty():
                        t1.join()
                        break
                except Exception as e:
                    print(e)
                    break
                try:
                    self.loop(stopSoon)
                except Exception as e:
                    import traceback
                    print("\n========== Fuzzer Loop Crash ==========")
                    traceback.print_exc()
                    print("=======================================\n")
                    self.logger.info(e)
                    break
        stopSoon.put(True)
        # write data to db
        result_data = {}
        result_data['totalSystemTestFailed'] = ShowStats.totalSystemTestFailed
        result_data['totalSystemTestFailed_Type1'] = ShowStats.totalSystemTestFailed_Type1
        result_data['totalSystemTestFailed_Type2'] = ShowStats.totalSystemTestFailed_Type2
        result_data['totalSystemTestFailed_Type3'] = ShowStats.totalSystemTestFailed_Type3
        result_data['system_testcase_num'] = ShowStats.totalSystemTestcases
        if self.testValidator.useMongo == 'True':
            self.testValidator.mongoDb.insert_result_to_db(result_data)
            # save exception map
            self.testValidator.mongoDb.insert_exception_to_db(self.testValidator.sysTester.exceptionMap)
            self.logger.info(f'map reason is: {self.testValidator.sysTester.exceptionMapReason}')
            self.testValidator.mongoDb.insert_map_to_db("ExceptionMapReason", self.testValidator.sysTester.exceptionMapReason)
        # save cov data
        # self.testValidator.mongoDb.insert_cov_unit_to_db(self.testValidator.covUnitData)
        # self.testValidator.mongoDb.insert_cov_sys_to_db(self.testValidator.covSysData)
        # self.testValidator.insert_data(self.testValidator.covUnitData, self.testValidator.covSysData)
        # delete execs for later test is accurate
        # self.testValidator.getCov.delete_execs()
        self.logger.info(f">>>>[fuzzer] hava a good time")
        print("\033[37m")
        if self.fuzzerConf['data_viewer'] == 'True':
            from utils.DataViewer import stopDrawing
            stopDrawing(self.dataViewer)

    def loop(self, stopSoon: Queue):
        """
        The loop function is the core of the fuzzer. It is meant to be run in a while loop,
        and it accomplishes the following:
            1. Generate a seed from our seed pool (see SeedPool class)
            2. Mutate this seed into multiple test cases using our TestcaseGenerator class (see TestcaseGenerator class)
            3. Run each of these test cases through our TestValidator and collect their results (see TestValidator class)

            If any result yields an interesting value, we add that seed back to our pool for future iterations.
        """
        # run time limit
        if time.time() - ShowStats.fuzzerStartTime > 3600 * int(Configuration.fuzzerConf['run_time']):
            # need to exit
            stopSoon.put(True)
        self.logger.info("Generator a Seed from SeedGenerator")
        self.seedGenerator.updateConfMutable()
        seed = self.seedGenerator.generateSeed()
        ShowStats.queueLength = len(self.seedGenerator.seedPool)
        testcasePerSeed = int(self.fuzzerConf['testcase_per_seed'])
        for _ in range(testcasePerSeed):
            self.logger.info(">>>>[fuzzer] start to mutate seed")
            self.logger.info(">>>>[fuzzer] seed len is : {}".format(seed.confItemList.__len__()))
            testcase = self.testcaseGenerator.mutate(seed)
            self.logger.info(">>>>[fuzzer] mutated testcase's length is : {}".format(len(testcase.confItemList)))
            utResult, sysResult, trimmedTestcase = self.testValidator.runTest(testcase, stopSoon)
            self.logger.info(">>>>[fuzzer] testValidator done")
            if (utResult != None) and (utResult.status == 1) and (sysResult != None) and (sysResult.status == 0):
                self.seedGenerator.addSeedToPool(trimmedTestcase)
            self.logger.info(">>>>[fuzzer] handle seed done")
            ShowStats.writeToPlotData()
            ShowStats.iterationCounts += 1
        ShowStats.loopCounts += 1
        # if ShowStats.loopCounts % 5 == 0:
        #     # gc on each five round
        #     gc.collect()
        self.logger.info("run() loop end -150")


if __name__ == "__main__":
    fuzzer = Fuzzer()
    fuzzer.run()
