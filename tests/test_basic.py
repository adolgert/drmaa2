import datetime
import getpass
import logging
import sys
import drmaa2


LOGGER = logging.getLogger("test_basic")


def test_manager():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    assert drmaa2.drmsName
    assert len(drmaa2.drmsName) > 0
    assert isinstance(drmaa2.drmsName, str)
    assert drmaa2.drmsVersion
    assert isinstance(drmaa2.drmsVersion[0], str)
    assert isinstance(drmaa2.drmsVersion[1], str)
    print(drmaa2.drmsName)
    print(drmaa2.drmsVersion)


def test_anonymous_job_session():
    js = drmaa2.JobSession()
    js.close()
    js.free()
    js.destroy()


def test_session():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    existing = drmaa2.JobSession.names()
    stage = "scalars"
    user = getpass.getuser()
    reported = user + "@" + stage
    if reported in existing:
        drmaa2.JobSession.destroy_named(stage)

    js = drmaa2.JobSession(stage)
    js.close()
    js.free()

    print(drmaa2.JobSession.names())

    jdel = drmaa2.JobSession.from_existing(stage)
    jdel.close()
    jdel.free()

    jdel.destroy()


def test_job_template_command():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    jt = drmaa2.JobTemplate()
    assert not jt.remoteCommand
    jt.remoteCommand = "/bin/true"
    assert jt.remoteCommand == "/bin/true"
    LOGGER.debug("setting to false")
    jt.remoteCommand = "/bin/false"
    assert jt.remoteCommand == "/bin/false"
    LOGGER.debug("Setting to None")
    jt.remoteCommand = None
    assert not jt.remoteCommand


def test_job_template_list():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    jt = drmaa2.JobTemplate()
    assert not jt.args
    jt.args = ["one", "two", "three"]
    assert jt.args == ["one", "two", "three"]
    jt.args = ["one", "two", "four"]
    assert jt.args == ["one", "two", "four"]
    jt.args = None
    assert not jt.args
    jt.args = []
    assert not jt.args


def test_job_template_bool():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    jt = drmaa2.JobTemplate()
    assert not jt.submitAsHold
    jt.submitAsHold = True
    assert jt.submitAsHold
    jt.submitAsHold = True
    assert jt.submitAsHold
    jt.submitAsHold = False
    assert not jt.submitAsHold


def test_job_template_dict():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    jt = drmaa2.JobTemplate()
    assert not jt.jobEnvironment
    jt.jobEnvironment = dict()
    assert not jt.jobEnvironment
    jt.jobEnvironment = {"PATH": "/bin:/homes/kheuton/bin", "LIB": "libm"}
    env = jt.jobEnvironment
    assert env["PATH"] == "/bin:/homes/kheuton/bin"
    assert "LIB" in env
    jt.jobEnvironment = {"SPACE": "race"}
    assert jt.jobEnvironment["SPACE"] == "race"
    assert len(jt.jobEnvironment) == 1


def test_job_template_enum():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    jt = drmaa2.JobTemplate()
    assert not jt.machineOS
    jt.machineOS = None
    assert not jt.machineOS
    jt.machineOS = "LINUX"
    assert jt.machineOS == "LINUX"
    jt.machineOS = "WIN"
    assert jt.machineOS == "WIN"
    jt.machineOS = None
    assert not jt.machineOS



def test_job_template_longlong():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    jt = drmaa2.JobTemplate()
    assert not jt.minSlots
    jt.minSlots = None
    assert not jt.minSlots
    jt.minSlots = 3
    assert jt.minSlots == 3
    jt.minSlots = 5
    assert jt.minSlots == 5
    jt.minSlots = None
    assert not jt.minSlots


def test_job_template_time():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    jt = drmaa2.JobTemplate()
    assert not jt.startTime
    jt.startTime = None
    assert not jt.startTime
    jt.startTime = datetime.datetime.now()
    assert jt.startTime
    jt.startTime = None
    assert not jt.startTime
    jt.startTime = "now"
    assert jt.startTime == "now"
    jt.startTime = "infinite"
    assert jt.startTime == "infinite"
    jt.startTime = "zero"
    assert jt.startTime == "zero"
    assert not jt.deadlineTime
