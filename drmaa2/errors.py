"""
Error handling and exceptions are here.
"""
import logging
from . import interface

LOGGER = logging.getLogger("drmaa2.errors")
DRMAA_LIB = interface.load_drmaa_library()


def last_error():
    """Gets the last error from DRMAA library.

    :return str: The text of an error message.
    """
    string_ptr = DRMAA_LIB.drmaa2_lasterror_text()
    if string_ptr:
        message = string_ptr.value.decode()
        DRMAA_LIB.drmaa2_string_free(string_ptr)
    else:
        message = None
    return message


def last_errno():
    """Gets the last error from DRMAA library.

    :return int: The error number which will match the Error enum.
    """
    error_idx = DRMAA_LIB.drmaa2_lasterror()
    try:
        return interface.Error(error_idx)
    except ValueError:
        return error_idx


def check_errno():
    if last_errno() != interface.Error.success:
        raise DRMAA2Exception(last_error())


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
        err_text = last_error()
        LOGGER.debug(err_text)
        if err_text:
            raise errs[errval](err_text)
        else:
            raise errs[errval]()
