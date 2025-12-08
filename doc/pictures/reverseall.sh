pyreverse -Smy --colorized --max-color-depth 5 -o pdf -p fuzzer ../../src/fuzzer.py
pyreverse -Amn -f ALL -o png -p dataModel ../../src/dataModel
pyreverse -Amn -f ALL -o png -p seedGenerator ../../src/seedGenerator
pyreverse -Amn -f ALL -o png -p testcaseGenerator ../../src/testcaseGenerator
pyreverse -Amn -f ALL -o png -p testValidator ../../src/testValidator
pyreverse -Amn -f ALL -o png -p utils ../../src/utils