# test

> This directory stores unit tests for codes in src.

## 执行所有单元测试

```bash
python performAllTests.py
```

## 利用graphviz+pycallgraph生成动态调用图

```bash
python generateCallGraphs.py
```

### 依赖安装

graphviz下载

http://www.graphviz.org/download/

python相关安装
```bash
conda install python-graphviz

# （可选）pycallgraph安装失败时，降级setuptools
# pip install --upgrade setuptools==57.5.0

pip install pycallgraph

# （可选）还原setuptools
# pip install --upgrade setuptools
```

## 利用coverage收集测试代码覆盖率

```bash
python measureCoverage.py
```

### 依赖安装
```bash
pip install coverage
```
