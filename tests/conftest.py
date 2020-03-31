import glob
import os
from shutil import rmtree

import pytest


@pytest.fixture(scope="session")
def clean_sampledir():
    os.chdir("samples")
    filelist = glob.glob(".coverage.*")
    for f in filelist:
        os.remove(f)
    os.chdir("..")


@pytest.fixture
def sampledir():
    old_cwd = os.getcwd()
    os.chdir("samples")
    if os.path.isdir("out"):
        rmtree("out")
    if os.path.isdir("debug"):
        rmtree("debug")
    yield
    if os.path.isdir("out"):
        rmtree("out")
    if os.path.isdir("debug"):
        rmtree("debug")
    os.chdir(old_cwd)
