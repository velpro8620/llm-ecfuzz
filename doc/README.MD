# 利用Sphinx自动生成API文档

## 依赖
```bash
pip install sphinx
```

## 编译并生成HTML
```bash
# 在doc目录下
make html
# 输出的html在build/html目录下，一般来说打开index.html就可以看到
```

## 源代码发生变动时重新生成模板文件
```bash
# linux（windows系统需要注意/和\的区别）
sphinx-apidoc -o source/rst ../src -f
```