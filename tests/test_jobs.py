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
    js.run(jt)
    jt.remoteCommand = Path("/bin/false")
    js.run(jt)
    js.close()
    js.free()
    js.destroy()
