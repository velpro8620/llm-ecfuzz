from dataModel.Seed import Seed
from dataModel.Testcase import Testcase
from testcaseGenerator.StackedMutator import Mutator
from utils.ShowStats import ShowStats
from dataModel.ConfItem import ConfItem


class TestcaseGenerator(object):
    """
    Testcase Generator is responsible for generating a testcase based on a given seed.
    A Testcase Generator may have different implements via different combination of mutators and constraintMaps.
    """

    def __init__(self, mutator: Mutator) -> None:
        self.mutator = mutator
        # self.seed_all = Seed()

    def mutate(self, seed: Seed) -> Testcase:
        """
        Perform some mutation on the configuration items of a seed, so as to generate a testcase.
        Based on the constraint map it contains.

        Args:
            seed (Seed): a seed needed to be mutated.

        Returns:
            testcase (Testcase): a new testcase.
        """
        ShowStats.currentJob = 'mutating'
        conf1 = ConfItem('fs.defaultFS','PORT','hdfs://127.0.0.1:9000')
        conf2 = ConfItem('hbase.rootdir','DIRPATH','/home/hadoop/hbase-2.2.2-work/hbase-tmp')
        if seed.__contains__(conf1):
            seed.confItemList.remove(conf1)
        if seed.__contains__(conf2):
            seed.confItemList.remove(conf2) 
            
        return self.mutator.mutate(seed)
