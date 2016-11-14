import datetime
import getpass
import logging
from pathlib import Path
import sys
import drmaa2


LOGGER = logging.getLogger("test_basic")


def test_run_job():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    js = drmaa2.JobSession()

    jt = drmaa2.JobTemplate()
    jt.remoteCommand = Path("/bin/true")
    job1 = js.run(jt)
    jt.remoteCommand = Path("/bin/false")
    job2 = js.run(jt)
    print(job1, job2)
    js.close()
    js.free()
    js.destroy()


def test_make_job():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    j = drmaa2.Job(id="234", sessionName="stage")
    assert j.id == "234"
    assert j.sessionName == "stage"
    j2 = drmaa2.Job.from_existing(j._wrapped)
    assert j2.id == "234"
    assert j2.sessionName == "stage"
