rm -rf build/
rm -rf dist/
rm -rf dgg_chat.egg-info/
python setup.py sdist bdist_wheel
twine upload dist/*
