import logging
import os
from multiprocessing import Pool
from shutil import rmtree

import pytest

from hough import __version__, analyse_file, run
from hough.cli import _abort
from hough.log_utils import start_logger_process


@pytest.mark.usefixtures("clean_sampledir")
def test_version():
    assert __version__ == "0.2.1"


@pytest.mark.usefixtures("sampledir")
def test_histogram_exception(mocker):
    mocker.patch("hough.histogram", new=RuntimeError("Boom"))
    assert run(["--histogram", "av-000.tif"]) == -1


@pytest.mark.usefixtures("sampledir")
def test_null_histogram():
    assert run(["--histogram", "white.jpg"]) == 0


@pytest.mark.usefixtures("sampledir")
def test_abort():
    logq, listener = start_logger_process(logging.DEBUG, "null.csv")
    with Pool(processes=2) as p:
        _abort(p, logq, listener)
    with Pool(processes=2) as p:
        _abort(p, 123, "abc")
    with Pool(processes=2) as p:
        _abort(p, None, None)
    _abort(123, 456, "abc")


@pytest.mark.usefixtures("sampledir")
def test_no_valid_files():
    run(["a", "b", "c"])


@pytest.mark.usefixtures("sampledir")
def test_vert():
    results = analyse_file("av-000.tif")
    res = results[0]
    assert res[0] == "av-000.tif"
    assert res[1] == ""
    assert res[2] > -2 and res[2] <= 0.0
    assert res[3] == ""
    # assert(res[4] == 928)
    # assert(res[5] == 1290)


@pytest.mark.usefixtures("sampledir")
def test_hv_fail():
    run(["av-001.jpg"])


@pytest.mark.usefixtures("sampledir")
def test_multifile_debug():
    rmtree("debug", ignore_errors=True)
    run(["--debug", "av-000.tif", "av-001.jpg"])
    assert os.path.exists("debug")
    assert os.path.exists("hough.log")
    # TODO: assert expected output appears under debug/DATE/whatever


@pytest.mark.usefixtures("sampledir")
def test_unstraightenable():
    run(["--debug", "binder.png"])
    assert os.path.exists("hough.log")
    os.remove("hough.log")
    rmtree("debug", ignore_errors=True)


@pytest.mark.usefixtures("sampledir")
def test_unstraightenable_nodebug():
    run(["binder.png"])


@pytest.mark.usefixtures("sampledir")
def test_histogram_verbose():
    run(["--histogram", "--verbose", "av-000.tif"])


@pytest.mark.usefixtures("sampledir")
def test_rgb_pdf_4_workers():
    if os.path.exists("./__pytest.csv"):
        os.remove("./__pytest.csv")
    run(
        [
            "--debug",
            "--results=./__pytest.csv",
            "--workers=4",
            "Newman_Computer_Exchange_VAX_PC_PDP11_Values.pdf",
        ]
    )
    assert os.path.exists("./__pytest.csv")
    assert os.path.exists("hough.log")
    os.remove("./__pytest.csv")
    os.remove("hough.log")
    rmtree("debug", ignore_errors=True)


@pytest.mark.usefixtures("sampledir")
def test_form_pdf():
    run(["i-9.pdf"])


@pytest.mark.usefixtures("sampledir")
def test_mixed_pdf():
    run(["i-9-paper-version.pdf"])


@pytest.mark.usefixtures("sampledir")
def test_white():
    run(["white.jpg"])


@pytest.mark.usefixtures("sampledir")
def test_unknown():
    run(["../README.md"])


@pytest.mark.usefixtures("sampledir")
def test_broken_out():
    open(".__pytest", "a").close()
    assert run(["--out=.__pytest", "white.jpg"]) == -1
    os.remove(".__pytest")


@pytest.mark.usefixtures("sampledir")
def test_no_args():
    assert run([]) == 0


@pytest.mark.usefixtures("sampledir")
def test_rotate_nothing():
    if os.path.exists(".__pytest"):
        os.remove(".__pytest")
    open(".__pytest", "a").close()
    assert run(["--rotate", "--results=.__pytest"]) == -1
    os.remove(".__pytest")


@pytest.mark.usefixtures("sampledir")
def test_rotate():
    if os.path.exists(".__pytest.dir"):
        rmtree(".__pytest.dir")
    run(
        [
            "--rotate",
            "--out=.__pytest.dir",
            "Newman_Computer_Exchange_VAX_PC_PDP11_Values.pdf",
            "av-000.tif",
        ]
    )
    assert os.path.exists(".__pytest.dir")
    assert os.path.exists(".__pytest.dir/results.csv")
    assert os.path.exists(
        ".__pytest.dir/Newman_Computer_Exchange_VAX_PC_PDP11_Values.pdf"
    )
    assert os.path.exists(".__pytest.dir/av-000.tif")
    rmtree(".__pytest.dir")


@pytest.mark.usefixtures("sampledir")
def test_rotate_from_results():
    if os.path.exists(".__pytest.dir"):
        rmtree(".__pytest.dir")
    assert run(["--rotate", "--out=.__pytest.dir", "--results=newman-results.csv"]) == 0
    assert os.path.exists(
        ".__pytest.dir/Newman_Computer_Exchange_VAX_PC_PDP11_Values.pdf"
    )
    rmtree(".__pytest.dir")
