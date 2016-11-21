import drmaa2
import logging
import pytest


LOGGER = logging.getLogger("test_innards")


def test_compare_structure():
    a = drmaa2.interface.DRMAA2_JINFO()
    b = drmaa2.interface.DRMAA2_JINFO()
    assert a == b
    a.exitStatus = 1
    assert a != b
    b.exitStatus = 1
    assert a == b
    a.jobId = b"123"
    b.jobId = b"123"
    assert a == b


def test_list_action():
    logging.basicConfig(level=logging.DEBUG)
    a = ["hi", "there", "bob"]
    l = drmaa2.DRMAA2List(a)
    LOGGER.debug(type(l))
    assert len(l) == 3
    assert l[0] == "hi"
    assert l[1] == "there"
    assert l[2] == "bob"
    b = list(l)
    assert b == a
    LOGGER.debug(type(b))


def test_job_compare():
    logging.basicConfig(level=logging.DEBUG)
    a = drmaa2.Job("123", "hi")
    b = drmaa2.interface.DRMAA2_J()
    b.id = b"123"
    b.sessionName = b"hi"
    # You have to compare the drmaa wrapper first b/c it has a compare
    # method that accounts for the different strings.
    assert b == a
    b.sessionName = b"howdy"
    assert b != a


def test_job_list():
    logging.basicConfig(level=logging.DEBUG)
    jobs = [drmaa2.Job(str(i), "hi"+str(i)) for i in range(123, 127)]
    job_list = drmaa2.DRMAA2List(jobs, "joblist")
    assert len(jobs) == len(job_list)
    assert jobs[3] == job_list[3]


def test_jinfo_memory():
    drmaa2.session._jinfo_crash()


def test_jinfo_object_memory():
    ji = drmaa2.session.JobInfo()
    ji.__del__()
