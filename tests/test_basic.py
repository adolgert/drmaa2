import getpass
import logging
import sys
import drmaa2

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

    print(drmaa2.JobSession.names())

    jdel = drmaa2.JobSession.from_existing(stage)
    jdel.close()

    jdel.destroy()
