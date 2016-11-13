from . import interface
from .session import *

DRMAA_LIB = interface.load_drmaa_library()

drmsName = DRMAA_LIB.drmaa2_get_drms_name().decode()
drmsVersion = [DRMAA_LIB.drmaa2_get_drms_version().contents.major.decode(),
               DRMAA_LIB.drmaa2_get_drms_version().contents.minor.decode()]
