from . import interface
from .interface import (CPU, Event, ListType, OS, JState,
                        Times, ResourceLimits, DRMAA2_CALLBACK)
from .session import (Job, job_template_implementation_specific,
                      JobTemplate, describe,
                      Notification, JobSession)
from .wrapping import (DRMAA2List, register_event_notification,
                       unset_event_notification)
from . import wrapping
from .errors import *


drmsName = wrapping.drms_name()
drmsVersion = wrapping.drms_version()
