from setuptools import setup
from os import path
from shutil import copy
import configparser

folder = path.dirname(path.realpath(__file__))

copy(f"{folder}/config.ini.sample", f"{folder}/config.ini")

input("Done. You can now start the bot.")
