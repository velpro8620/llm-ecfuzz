import unittest

from dataModel.ConfItem import ConfItem


class testConfItem(unittest.TestCase):
    def testCreator(self):
        confItem = ConfItem("lisy", "帅哥", "确实")
        print(confItem)

    def testProperty(self):
        confItem = ConfItem()
        confItem.name = "lisy"
        print(confItem.name)
        confItem.type = "帅哥"
        print(confItem.type)
        confItem.value = "确实"
        print(confItem.value)

    def test__str__(self):
        confItem = ConfItem("lisy", "帅哥", "确实")
        print(confItem.__str__())

    def test__eq__(self):
        confItem = ConfItem("lisy", "帅哥", "确实")
        confItem2 = ConfItem("lijq", "帅哥", "确实")
        print(confItem == confItem2)
        print(confItem == 3)



if __name__ == '__main__':
    unittest.main()
