import atexit
import logging
from . import interface
from .session import *
from .errors import *


LOGGER = logging.getLogger("drmaa2")
DRMAA_LIB = interface.load_drmaa_library()


def drms_name():
    if DRMAA_LIB:
        return_str(DRMAA_LIB.drmaa2_get_drms_name())
    else:
        return None


def drms_version():
    if not DRMAA_LIB:
        return None
    LOGGER.debug("enter drms_version")
    version_ptr = DRMAA_LIB.drmaa2_get_drms_version()
    version = version_ptr.contents
    value = (version.major.value.decode(), version.minor.value.decode())
    DRMAA_LIB.drmaa2_version_free(byref(version_ptr))
    LOGGER.debug("leave drms_version")
    return value


def event_callback(cb):
    """You don't want to have to write a callback function that
    decodes the C structs, so this decodes the values and sends
    them gently to the actual callback."""
    def wrapper(notification_ptr):
        notification = Notification(notification_ptr.contents)
        cb(notification.event, notification.jobId, notification.sessionName,
           notification.jobState)
        DRMAA_LIB.drmaa2_notification_free(notification_ptr)
    return wrapper


def register_event_notification(callback):
    """Register to receive notifications of events for new states,
    migration, or change of attributes.
    Unsupported in Univa Grid Engine"""
    callback_ptr = DRMAA2_CALLBACK(event_callback(callback))
    LOGGER.debug("callback is {}".format(callback_ptr))
    CheckError(DRMAA_LIB.drmaa2_register_event_notification(callback_ptr))
    atexit.register(unset_event_notification)


def unset_event_notification():
    LOGGER.debug("unset event notification")
    CheckError(DRMAA_LIB.drmaa2_register_event_notification(DRMAA2_CALLBACK()))


drmsName = drms_name()
drmsVersion = drms_version()
