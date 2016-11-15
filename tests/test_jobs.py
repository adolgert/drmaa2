import datetime
import getpass
import logging
from pathlib import Path
import sys
import pytest
import drmaa2


LOGGER = logging.getLogger("test_jobs")


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
    # The error is that spaces aren't allowed.
    with pytest.raises(RuntimeError):
        with drmaa2.JobSession() as js:
            jt = drmaa2.JobTemplate()
            jt.remoteCommand = Path("/bin/sleep")
            jt.args = ["60"]
            jt.minSlots = 2
            jobs = list()
            for idx in range(3):
                if idx > 0:
                    previous = jobs[-1].id
                    pe_str = "-pe multi_slot -hold_jid={}".format(previous)
                    LOGGER.debug("Using pe string: {}".format(pe_str))
                    jt.set_impl_spec("uge_jt_pe", pe_str)
                    jobs.append(js.run(jt))
                    print("Returned job is {}".format(jobs[-1]))
                else:
                    LOGGER.debug("submitting job {} {}".format(idx, jt))
                    jobs.append(js.run(jt))
                    print("Returned job is {}".format(jobs[-1]))


def test_submit_with_impl_spec():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    # The error is that spaces aren't allowed.
    with pytest.raises(RuntimeError):
        with drmaa2.JobSession() as js:
            jt = drmaa2.JobTemplate()
            jt.remoteCommand = Path("/bin/sleep")
            jt.args = ["60"]
            jt.minSlots = 2
            jobs = list()
            for idx in range(3):
                if idx > 0:
                    previous = jobs[-1].id
                    pe_str = "-pe multi_slot -hold_jid={}".format(previous)
                    LOGGER.debug("Using pe string: {}".format(pe_str))
                    jt.implementationSpecific = pe_str
                    jobs.append(js.run(jt))
                    print("Returned job is {}".format(jobs[-1]))
                else:
                    LOGGER.debug("submitting job {} {}".format(idx, jt))
                    jobs.append(js.run(jt))
                    print("Returned job is {}".format(jobs[-1]))



def test_submit_with_pe():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    with drmaa2.JobSession() as js:
        jt = drmaa2.JobTemplate()
        jt.remoteCommand = Path("/bin/sleep")
        jt.args = ["60"]
        jt.set_impl_spec("uge_jt_pe", "multi_slot")
        for run_idx in range(3):
            js.args = str(60+run_idx)
            job = js.run(jt)
            LOGGER.debug("Ran job {}".format(job))
            assert job


def test_wait_terminated():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    with drmaa2.JobSession() as js:
        jt = drmaa2.JobTemplate()
        jt.remoteCommand = Path("/bin/sleep")
        jt.args = ["30"]
        jobs = list()
        job_cnt = 2
        for idx in range(job_cnt):
            LOGGER.debug("submitting job {} {}".format(idx, jt))
            jobs.append(js.run(jt))
            print("submitted job is {}".format(jobs[-1]))

        job_list = drmaa2.DRMAA2List(jobs, "joblist")
        returned = list()
        # This should remove completed jobs from the list every
        # time one is returned, as shown in src/hold.c.
        for reap_idx in range(job_cnt):
            job = None
            while not job:
                job = js.wait_any_terminated(job_list, 10)
                LOGGER.debug("Returned from wait {}".format(job))
            returned.append(job)
            LOGGER.debug("completed: {}".format(returned[-1]))
        assert returned[0] != returned[1]
