from . import interface
from .session import *

DRMAA_LIB = interface.load_drmaa_library()

drmsName = return_str(DRMAA_LIB.drmaa2_get_drms_name())
drmsVersion = drms_version()
