import datetime
import getpass
import logging
from pathlib import Path
import sys
import pytest
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
    js.__del__()
    js.destroy()


def test_make_job():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    j = drmaa2.Job(id="234", sessionName="stage")
    assert j.id == "234"
    assert j.sessionName == "stage"


class Counter:
    def __init__(self):
        self.count = 0
    def __call__(self, event, jobId, session, job_state):
        self.count +=1
        print(event, jobId, session, job_state)


def test_notification():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    with pytest.raises(drmaa2.UnsupportedOperation):
        drmaa2.register_event_notification(Counter())


def test_submit_with_hold():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    with drmaa2.JobSession() as js:
        jt = drmaa2.JobTemplate()
        jt.remoteCommand = Path("/bin/sleep")
        jt.args = ["60"]
        jt.minSlots = 2
        jobs = list()
        for idx in range(3):
            if idx > 0:
                drmaa2.
                jt.pe = "multi_slot"
                LOGGER.debug("submitting job PE {} {}".format(idx, jt))
                jobs.append(js.run(jt))
                print("Returned job is {}".format(jobs[-1]))
            else:
                LOGGER.debug("submitting job {} {}".format(idx, jt))
                jobs.append(js.run(jt))
                print("Returned job is {}".format(jobs[-1]))


def test_wait_terminated():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    with drmaa2.JobSession() as js:
        jt = drmaa2.JobTemplate()
        jt.remoteCommand = Path("/bin/sleep")
        jt.args = ["60"]
        jobs = list()
        for idx in range(5):
            if idx > 0:
                jt.pe = "-hold_jid={}".format(jobs[-1].id)
                LOGGER.debug("submitting job PE {} {}".format(idx, jt))
                jobs.append(js.run(jt))
                print("Returned job is {}".format(jobs[-1]))
            else:
                LOGGER.debug("submitting job {} {}".format(idx, jt))
                jobs.append(js.run(jt))
                print("Returned job is {}".format(jobs[-1]))

        job_list = drmaa2.DRMAA2List(jobs, "joblist")
        returned = list()
        for reap_idx in range(5):
            returned.append(js.wait_any_terminated(job_list, "infinite"))
