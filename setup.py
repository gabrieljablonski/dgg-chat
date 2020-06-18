from setuptools import setup, find_packages
from pathlib import Path

from dgg_chat import __version__

long_description = Path('README.md').read_text()

setup(
    name='dgg-chat',
    packages=find_packages(),
    version=__version__,
    license='MIT',
    description='A package that lets you do stuff in dgg chat',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Gabriel Jablonski',
    author_email='contact@gabrieljablonski.com',
    url='https://github.com/gabrieljablonski/dgg-chat',
    download_url='https://github.com/gabrieljablonski/dgg-chat/archive/v0.1.0-alpha.tar.gz',    # I explain this later on
    keywords=['chat-bot', 'chat', 'destinygg', 'dgg'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
    ],
    python_requires='>=3.8',
    install_requires=[
        'websocket_client', 
        'requests',
        'numpy', 'wsaccel'  # improve websockets performance
    ],
)
