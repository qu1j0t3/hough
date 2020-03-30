import logging
import os
from multiprocessing import Pool
from shutil import rmtree

from hough import __version__
from hough.cli import _abort, run
from hough.log_utils import start_logger_process
from hough.process import process_file


def test_version():
    assert __version__ == "0.2.0"


def test_histogram_exception(mocker):
    mocker.patch("hough.cli.histogram", new=RuntimeError("Boom"))
    assert run(["--histogram", "samples/av-000.tif"]) == -1


def test_null_histogram():
    assert run(["--histogram", "samples/white.jpg"]) == 0


def test_abort():
    logq, listener = start_logger_process(logging.DEBUG, "null.csv")
    with Pool(processes=2) as p:
        _abort(p, logq, listener)
    with Pool(processes=2) as p:
        _abort(p, 123, "abc")
    with Pool(processes=2) as p:
        _abort(p, None, None)
    _abort(123, 456, "abc")


def test_vert():
    results = process_file("samples/av-000.tif")
    res = results[0]
    assert res[0] == "samples/av-000.tif"
    assert res[1] == ""
    assert res[2] > -1.05 and res[2] <= 0.0
    assert res[3] == ""
    # assert(res[4] == 928)
    # assert(res[5] == 1290)


def test_hv_fail():
    run(["samples/av-001.jpg"])


def test_multifile_debug():
    rmtree("debug", ignore_errors=True)
    run(["--debug", "samples/av-000.tif", "samples/av-001.jpg"])
    assert os.path.exists("debug")
    assert os.path.exists("hough.log")
    # TODO: assert expected output appears under debug/DATE/whatever


def test_unstraightenable():
    run(["--debug", "samples/binder.png"])
    assert os.path.exists("hough.log")
    os.remove("hough.log")
    rmtree("debug", ignore_errors=True)


def test_unstraightenable_nodebug():
    run(["samples/binder.png"])


def test_histogram_verbose():
    run(["--histogram", "--verbose", "samples/av-000.tif"])


def test_rgb_pdf_4_workers():
    run(
        [
            "-c",
            "--debug",
            "--results=__pytest",
            "--workers=4",
            "samples/Newman_Computer_Exchange_VAX_PC_PDP11_Values.pdf",
        ]
    )
    assert os.path.exists("__pytest.csv")
    assert os.path.exists("hough.log")
    os.remove("__pytest.csv")
    os.remove("hough.log")
    rmtree("debug", ignore_errors=True)


def test_form_pdf():
    run(["samples/i-9.pdf"])


def test_mixed_pdf():
    run(["samples/i-9-paper-version.pdf"])


def test_white():
    run(["samples/white.jpg"])


def test_unknown():
    run(["README.md"])
