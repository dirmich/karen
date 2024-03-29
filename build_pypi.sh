#!/bin/sh

pandoc --from=markdown --to=rst --output=README.rst README.md
rm dist/*.*
python3 setup.py sdist bdist_wheel
twine upload --repository pypi dist/*
