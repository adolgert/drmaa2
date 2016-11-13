import logging
from ctypes import cast
from .interface import *


LOGGER = logging.getLogger("drmaa2.session")
DRMAA_LIB = load_drmaa_library()


class DRMAA2Exception(Exception):
    pass


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


class JobSession:
    def __init__(self, name):
        """The IDL description says this should have a contact name,
        but it isn't supported."""
        assert isinstance(name, str)
        LOGGER.debug("Creating JobSession {}".format(name))
        self._session = DRMAA_LIB.drmaa2_create_jsession(
            name.encode(), c_char_p()
        )
        if not self._session:
            raise RuntimeError(
                DRMAA_LIB.drmaa2_lasterror_text().decode()
            )
        self.name = name

    @classmethod
    def from_existing(cls, name):
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
        return contact_str.decode()


def create_job_session():
    lib = load_drmaa2()
    print(lib)
    print(lib.drmaa2_create_jsession)


