# 利用 graphviz+pylink 自动生成UML图

## 依赖安装

graphviz下载

http://www.graphviz.org/download/

python相关安装
```bash
conda install python-graphviz

conda install pylint
```

## 生成
```bash
# 在当前目录下
pyreverse -Smy --colorized --max-color-depth 5 -o pdf -p fuzzer ../../src/fuzzer.py
pyreverse -ASmn -f ALL -o png -p dataModel ../../src/dataModel
pyreverse -ASmn -f ALL -o png -p seedGenerator ../../src/seedGenerator
pyreverse -ASmn -f ALL -o png -p testcaseGenerator ../../src/testcaseGenerator
pyreverse -ASmn -f ALL -o png -p testValidator ../../src/testValidator
pyreverse -ASmn -f ALL -o png -p utils ../../src/utils

```

简单操作
```bash
# 在当前目录下
sh reverseall.sh
```
