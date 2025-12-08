import os
from logging import raiseExceptions
from dataModel.Seed import Seed
from dataModel.Testcase import Testcase
from dataModel.ConfItem import ConfItem
from testcaseGenerator.Mutator import Mutator
import random, logging
from utils.NewValue import NewValue
from utils.ConfAnalyzer import ConfAnalyzer
from utils.UnitConstant import DATA_DIR
from utils.ShowStats import ShowStats
from utils.Logger import Logger

class StackedMutator(Mutator):
    def __init__(self) -> None:
        super().__init__()
        self.logger: logging.Logger = Logger.get_logger()

    def findConfItem(self, seed: Seed, confName: str):
        confItemIndex = -1
        res = ConfItem()
        for index in range(0, len(seed.confItemList)):
            conf = seed.confItemList[index]
            if confName == conf.name:
                res.name = conf.name
                res.value = conf.value
                res.type = conf.type
                confItemIndex = index
                break
        if confItemIndex == -1:
            return confItemIndex, None
        else:
            return confItemIndex, res

    def mutate(self, seed: Seed) -> Testcase:
        """

        """
        testcase = Testcase()
        number = [i for i in range(3, 6)]
        mutate_num = number[random.randint(0, len(number) - 1)]

        item_dict = {}
        dependency = ConfAnalyzer.confItemRelations
        newValue = NewValue()
        # index_list = random.sample(range(0, len(seed.confItemList)), mutate_num)

        for times in range(0, mutate_num):
            choose_conf_index = random.randint(0, len(seed.confItemList) - 1)
            conf = seed.confItemList[choose_conf_index]
            itemA = ConfItem()
            itemA.name = conf.name
            itemA.type = conf.type
            itemA.value = conf.value
            self.logger.info(f"<<<<[StackedMutator] for itemA conf name is : {itemA.name}; conf value is : {itemA.value}; conf type is : {itemA.type}")
            if conf.name in dependency.keys():
                for one in dependency[conf.name]:
                    confItemIndex, itemB = self.findConfItem(seed, one[0])
                    if confItemIndex == -1:
                        ConfAnalyzer.confMutationInfo[itemA.name][0] += 1
                        ShowStats.nowTestConfigurationName = conf.name
                        ShowStats.nowMutationType = conf.type
                        itemA.value = newValue.genValue(conf.type, conf.value)
                    else:
                        ConfAnalyzer.confMutationInfo[itemB.name][0] += 1
                        self.logger.info(f"<<<<[StackedMutator] for itemB conf name is : {itemB.name}; conf value is : {itemB.value}; conf type is : {itemB.type}")
                        newValue.constraint_method(one[1], itemA, itemB)
                        self.logger.info(f"<<<<[StackedMutator] for new itemB conf name is : {itemB.name}; conf value is : {itemB.value}; conf type is : {itemB.type}")
                        itemB.isMutated = True
                        item_dict[confItemIndex] = itemB
            else:
                ShowStats.nowTestConfigurationName = conf.name
                ShowStats.nowMutationType = conf.type
                itemA.value = newValue.genValue(conf.type, conf.value)
                # if (len(mutated_value_list)):
                #     new_value = mutated_value_list[random.randint(0, len(mutated_value_list) - 1)]
                #     co.value = str(new_value)
            itemA.isMutated = True
            item_dict[choose_conf_index] = itemA
            self.logger.info(f"<<<<[StackedMutator] for new itemA conf name is : {itemA.name}; conf value is : {itemA.value}; conf type is : {itemA.type}")
        for index in range(0, len(seed.confItemList)):
            if index in item_dict.keys():
                testcase.confItemList.append(item_dict[index])
                ConfAnalyzer.confMutationInfo[item_dict[index].name][0] += 1
            else:
                testcase.confItemList.append(seed.confItemList[index])
        return testcase