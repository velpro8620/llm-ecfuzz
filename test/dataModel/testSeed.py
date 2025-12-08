import unittest

from dataModel.ConfItem import ConfItem
from dataModel.Seed import Seed


class testSeed(unittest.TestCase):
    def test__getitem__(self):
        seed = Seed()
        seed.confItemList.append(ConfItem("lisy", "帅哥", "确实"))
        print(seed[0])

    def test__setitem__(self):
        seed = Seed()
        seed.confItemList.append(ConfItem("lisy", "帅哥", "确实"))
        seed[0] = ConfItem("lijq", "帅哥", "确实")
        print(seed)

    def test__contains__(self):
        seed = Seed()
        seed.confItemList.append(ConfItem("lisy", "帅哥", "确实"))
        assert seed.__contains__(ConfItem("lisy", "帅哥", "确实"))

    def testIndexOutOfBounds(self):
        seed = Seed()
        seed.confItemList.append(ConfItem("lisy", "帅哥", "确实"))
        assert seed[1] == ConfItem()

    def testAddConfItem(self):
        seed = Seed()
        seed.addConfItem(ConfItem("lisy", "帅哥", "确实"))

if __name__ == '__main__':
    unittest.main()
