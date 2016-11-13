"""
This creates classes around the Session interface of
the DRMAA2 library using the interface module to
provide access to the native library.
"""
import logging
from ctypes import cast
from .interface import *


LOGGER = logging.getLogger("drmaa2.session")
DRMAA_LIB = load_drmaa_library()


def drms_version():
    LOGGER.debug("enter drms_version")
    version_ptr = DRMAA_LIB.drmaa2_get_drms_version()
    version = version_ptr.contents
    value = (version.major.value.decode(), version.minor.value.decode())
    DRMAA_LIB.drmaa2_version_free(pointer(version_ptr))
    LOGGER.debug("leave drms_version")
    return value


class DRMAA2Exception(Exception):
    """Base class so a user can catch all DRMAA2 exceptions."""
    pass


# These exceptions are defined by the IDL Spec.
class DeniedByDrms(DRMAA2Exception):
    """The DRM system rejected the operation due to security issues."""


class DrmCommunication(DRMAA2Exception):
    """The DRMAA implementation could not contact the DRM system. The
    problem source is unknown to the implementation, so it is unknown if the
    problem is transient or not."""


class TryLaterException(DRMAA2Exception):
    """The DRMAA implementation detected a transient problem while
    performing the operation, for example due to excessive load. The
    application is recommended to retry the operation."""


class SessionManagement(DRMAA2Exception):
    """Not in the IDL. Found in UGE header."""


class Timeout(DRMAA2Exception):
    """The timeout given in one the waiting functions was reached without
    successfully finishing the waiting attempt."""


class InternalError(DRMAA2Exception):
    """Undefined DRMAA interal error."""


class InvalidSession(DRMAA2Exception):
    """The session used for the method call is not valid, for example since
    the session was previously closed."""


class InvalidState(DRMAA2Exception):
    """The operation is not allowed in the current state of the job."""


class OutOfResource(DRMAA2Exception):
    """The implementation has run out of operating system resources, such as
    buffers, main memory, or disk space."""


class UnsupportedAttribute(DRMAA2Exception):
    """The optional attribute is not supported by this DRMAA implementation."""


class UnsupportedOperation(DRMAA2Exception):
    """The method is not supported by this DRMAA implementation."""


class ImplementationSpecific(DRMAA2Exception):
    """The implementation needs to report a special error condition that
    cannot be mapped to one of the other exceptions."""


def CheckError(errval):
    """Quick check of return values that throws a DRMAA2Exception."""
    errs = {
        1: DeniedByDrms,
        2: DrmCommunication,
        3: TryLaterException,
        4: SessionManagement,
        5: Timeout,
        6: InternalError,
        7: ValueError,
        8: InvalidSession,
        9: InvalidState,
        10: OutOfResource,
        11: UnsupportedAttribute,
        12: UnsupportedOperation,
        13: ImplementationSpecific
    }
    if errval > 0:
        err_text = DRMAA_LIB.drmaa2_lasterror_text().decode()
        LOGGER.debug(err_text)
        raise errs[errval](err_text)


class JobTemplate:
    """A JobTemplate is both how to specify a job and how to search for jobs.
    """
    def __init__(self):
        self.remoteCommand = None
        self.args = None
        self.submitAsHold = None
        self.rerunnable = None
        self.jobEnvironment = None
        self.workingDirectory = None
        self.jobCategory = None
        self.email = None
        self.emailOnStarted = None
        self.emailOnTerminated = None
        self.jobName = None
        self.inputPath = None
        self.outputPath = None
        self.errorPath = None
        self.joinFiles = None
        self.reservationId = None
        self.queueName = None
        self.minSlots = None
        self.maxSlots = None
        self.priority = None
        self.candidateMachines = None
        self.minPhysMemory = None
        self.machineOS = None
        self.machineArch = None
        self.startTime = None
        self.deadlineTime = None
        self.stageInFiles = None
        self.stageOutFiles = None
        self.resourceLimits = None
        self.accountingId = None
        self.jt_pe = None

    def as_structure(self):
        structure = DRMAA2_JTEMPLATE()
        structure.remoteCommand = str(self.remoteCommand).encode()
        if self.args:
            structure.args = " ".join(self.args).encode()
        else:
            structure.args = UNSET_STRING
        if self.submitAsHold is not None:
            if self.submitAsHold:
                structure.submitAsHold = Bool.true.value
            else:
                structure.submitAsHold = Bool.false.value
        else:
            structure.submitAsHold = UNSET_BOOL


class JobSession:
    def __init__(self, name, contact=None):
        """The IDL description says this should have a contact name,
        but it isn't supported. UGE always makes the contact your
        user name."""
        assert isinstance(name, str)
        LOGGER.debug("Creating JobSession {}".format(name))
        if contact:
            contact_str = contact.encode()
        else:
            contact_str = c_char_p()
        self._session = DRMAA_LIB.drmaa2_create_jsession(
            name.encode(), contact_str
        )
        if not self._session:
            raise RuntimeError(
                DRMAA_LIB.drmaa2_lasterror_text().decode()
            )
        self.name = name

    @classmethod
    def from_existing(cls, name):
        """If user tangkend made JobSession crunch, then
        the job would be listed here as tangkend@crunch."""
        session = DRMAA_LIB.drmaa2_open_jsession(name.encode())
        if not session:
            raise RuntimeError(
                DRMAA_LIB.drmaa2_lasterror_text().decode()
            )
        # Skip the __init__ if this job session already exists.
        obj = cls.__new__(cls)
        obj._session = session
        obj.name = name
        return obj

    @staticmethod
    def names():
        name_list = DRMAA_LIB.drmaa2_get_jsession_names()
        session_names = list()
        if name_list:
            session_cnt = DRMAA_LIB.drmaa2_list_size(name_list)
            LOGGER.debug("There are {} sessions".format(session_cnt))
            for session_idx in range(session_cnt):
                void_p = DRMAA_LIB.drmaa2_list_get(name_list, session_idx)
                name = cast(void_p, drmaa2_string).value.decode()
                session_names.append(name)
            LOGGER.debug("Retrieved names of sessions.")
        else:
            pass  # Nothing to return.
        return session_names

    def close(self):
        LOGGER.debug("close JobSession")
        CheckError(DRMAA_LIB.drmaa2_close_jsession(self._session))

    def destroy(self):
        LOGGER.debug("Destroying {}".format(self.name))
        CheckError(DRMAA_LIB.drmaa2_destroy_jsession(
            self.name.encode()))

    @staticmethod
    def destroy_named(name):
        LOGGER.debug("Destroying {}".format(name))
        CheckError(DRMAA_LIB.drmaa2_destroy_jsession(
            name.encode()))

    def free(self):
        LOGGER.debug("free JobSession")
        DRMAA_LIB.drmaa2_jsession_free(self._session)  # void

    @property
    def contact(self):
        contact_str = DRMAA_LIB.drmaa2_jsession_get_contact(self._session)
        if contact_str:
            return contact_str.decode()
        else:
            return None
