"""
This creates classes around the Session interface of
the DRMAA2 library using the interface module to
provide access to the native library.
"""
import logging
from copy import deepcopy
from ctypes import cast, byref
import datetime
from uuid import uuid4
from .interface import *


LOGGER = logging.getLogger("drmaa2.session")
DRMAA_LIB = load_drmaa_library()


def drms_version():
    LOGGER.debug("enter drms_version")
    version_ptr = DRMAA_LIB.drmaa2_get_drms_version()
    version = version_ptr.contents
    value = (version.major.value.decode(), version.minor.value.decode())
    DRMAA_LIB.drmaa2_version_free(byref(version_ptr))
    LOGGER.debug("leave drms_version")
    return value


def last_error():
    """Gets the last error from DRMAA library."""
    return return_str(DRMAA_LIB.drmaa2_lasterror_text())


def last_errno():
    """Gets the last error from DRMAA library."""
    return DRMAA_LIB.drmaa2_lasterror()


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
        raise errs[errval](err_text)


class DRMAA2Bool:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        wrapped_value = getattr(obj._wrapped.contents, self.name)
        return Bool(wrapped_value)==Bool.true

    def __set__(self, obj, value):
        setattr(obj._wrapped.contents, self.name, 1 if value else 0)


class DRMAA2String:
    """A descriptor for wrapped strings on structs.
    There is no drmaa2_string_create, so we use ctypes' own allocation
    and freeing, which happens by default."""
    def __init__(self, name):
        self.name = name
        self.was_set = False

    def __get__(self, obj, type=None):
        wrapped_value = getattr(obj._wrapped.contents, self.name).value
        if wrapped_value is None:  # Exclude case where it is "".
            return wrapped_value
        else:
            return wrapped_value.decode()

    def __set__(self, obj, value):
        wrapped_value = getattr(obj._wrapped.contents, self.name)
        if wrapped_value.value and not self.was_set:
            DRMAA_LIB.drmaa2_string_free(byref(wrapped_value))
        else:
            pass  # No need to free it if it's null.
        if value is not None:
            setattr(obj._wrapped.contents, self.name,
                    drmaa2_string(str(value).encode()))
            self.was_set = True
        else:
            setattr(obj._wrapped.contents, self.name, UNSET_STRING)

    def free(self):
        pass

def print_string_list(wrapped_list):
    string_cnt = DRMAA_LIB.drmaa2_list_size(wrapped_list)
    assert last_errno() < 1
    ptrs = list()
    vals = list()
    for string_idx in range(string_cnt):
        void_p = DRMAA_LIB.drmaa2_list_get(wrapped_list, string_idx)
        ptrs.append(void_p)
        assert last_errno() < 1
        name = cast(void_p, drmaa2_string).value.decode()
        vals.append(name)
    print(", ".join(vals))
    print(", ".join([str(x) for x in ptrs]))


class DRMAA2StringList:
    def __init__(self, name, list_type):
        """Name is the name of the member of the instance.
        list_type is the ListType enum for this list.
        If there isn't a list, we make one, so we free it, too."""
        assert isinstance(list_type, ListType)
        self.name = name
        self.list_type = list_type
        self.allocated = None

    def __get__(self, obj, type=None):
        wrapped_list = getattr(obj._wrapped.contents, self.name)
        if wrapped_list:
            string_list = list()
            string_cnt = DRMAA_LIB.drmaa2_list_size(wrapped_list)
            assert last_errno() < 1
            for string_idx in range(string_cnt):
                void_p = DRMAA_LIB.drmaa2_list_get(wrapped_list, string_idx)
                assert last_errno() < 1
                name = cast(void_p, drmaa2_string).value.decode()
                LOGGER.debug("{} at index {}".format(name, string_idx))
                string_list.append(name)
            return string_list
        else:
            return []

    def __set__(self, obj, value):
        wrapped = getattr(obj._wrapped.contents, self.name)
        if wrapped:
            name_cnt = DRMAA_LIB.drmaa2_list_size(wrapped)
            LOGGER.debug("Emptying string {} len {}".format(
                self.name, name_cnt))
            while name_cnt > 0:
                LOGGER.debug("Deleting from list")
                CheckError(DRMAA_LIB.drmaa2_list_del(wrapped, 0))
                name_cnt = DRMAA_LIB.drmaa2_list_size(wrapped)
        else:
            LOGGER.debug("Creating string {}".format(self.name))
            wrapped = DRMAA_LIB.drmaa2_list_create(
                self.list_type.value, DRMAA2_LIST_ENTRYFREE())
            self.allocated = wrapped
            setattr(obj._wrapped.contents, self.name, wrapped)

        if value:
            # In order to manage memory, attach the list to this object.
            self.value = [x.encode() for x in value]
            LOGGER.debug("Adding string {} values {}".format(self.name, value))
            string_obj = drmaa2_string()
            for idx in range(len(value)):
                LOGGER.debug("value going in {} at {}".format(
                    string_obj.value, string_obj))
                CheckError(DRMAA_LIB.drmaa2_list_add(
                    wrapped, self.value[idx]))

        print_string_list(wrapped)

    def free(self):
        if self.allocated:

            DRMAA_LIB.drmaa2_list_free(byref(self.allocated))


class DRMAA2Dict:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        wrapped = getattr(obj._wrapped.contents, self.name)
        if wrapped:
            key_list = DRMAA_LIB.drmaa2_dict_list(wrapped)
            if key_list:
                result = dict()
                key_cnt = DRMAA_LIB.drmaa2_list_size(key_list)
                for key_idx in range(key_cnt):
                    void_ptr = DRMAA_LIB.drmaa2_list_get(key_list, key_idx)
                    key_ptr = cast(void_ptr, drmaa2_string).value
                    value_ptr = DRMAA_LIB.drmaa2_dict_get(wrapped, key_ptr)
                    LOGGER.debug("{} {}".format(
                        key_ptr.decode(), value_ptr.decode()))
                    result[key_ptr.decode()] = value_ptr.decode()
                return result
            else:
                return dict()
        else:
            return dict()

    def __set__(self, obj, value):
        wrapped = getattr(obj._wrapped.contents, self.name)
        if not wrapped:
            wrapped = DRMAA_LIB.drmaa2_dict_create(DRMAA2_DICT_ENTRYFREE())
            setattr(obj._wrapped.contents, self.name, wrapped)
        else:
            key_list = DRMAA_LIB.drmaa2_dict_list(wrapped)
            if key_list:
                key_cnt = DRMAA_LIB.drmaa2_list_size(key_list)
                for key_idx in range(key_cnt):
                    void_ptr = DRMAA_LIB.drmaa2_list_get(key_list, key_idx)
                    key_ptr = cast(void_ptr, drmaa2_string).value
                    CheckError(DRMAA_LIB.drmaa2_dict_del(wrapped, key_ptr))

        self.dict = {(k.encode(), v.encode()) for (k, v) in value.items()}
        for key, value in self.dict:
            CheckError(DRMAA_LIB.drmaa2_dict_set(wrapped, key, value))


class DRMAA2LongLong:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        val = getattr(obj._wrapped.contents, self.name)
        if val == UNSET_NUM:
            return None
        else:
            return val

    def __set__(self, obj, value):
        if value is None:
            value = UNSET_NUM
        else:
            value = value
        setattr(obj._wrapped.contents, self.name, value)


class DRMAA2Enum:
    def __init__(self, name, enum_cls):
        self.name = name
        self.enum_cls = enum_cls

    def __get__(self, obj, type=None):
        name = self.enum_cls(getattr(obj._wrapped.contents, self.name)).name
        if name == "unset":
            return None
        else:
            return name

    def __set__(self, obj, value):
        value = value or "unset"
        setattr(obj._wrapped.contents, self.name, self.enum_cls[value].value)


class DRMAA2Time:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        LOGGER.debug("enter get time {}".format(self.name))
        time_ptr = getattr(obj._wrapped.contents, self.name)
        if time_ptr:
            print("have time_ptr")
            when = time_ptr
            print("have time_ptr contents {}".format(when.tm_sec))
            if when == UNSET_TIME:
                print("time is unset")
                return None
            else:
                print("have a real time")
                return datetime.datetime(
                    year = when.tm_year,
                    month = when.tm_mon,
                    day = when.tm_yday,
                    hour = when.tm_hour,
                    minute = when.tm_min,
                    second = when.tm_sec
                )
        else:
            return None

    def __set__(self, obj, value):
        LOGGER.debug("enter set time {} {}".format(self.name, value))
        time_ptr = getattr(obj._wrapped.contents, self.name)
        if time_ptr:
            when = value.timetuple()
            time_obj = time_ptr.contents
            time_obj.tm_sec = when.tm_sec
            time_obj.tm_min = when.tm_min
            time_obj.tm_hour = when.tm_hour
            time_obj.tm_mday = when.tm_mday
            time_obj.tm_mon = when.tm_mon
            time_obj.tm_year = when.tm_year
            time_obj.tm_wday = when.tm_wday
            time_obj.tm_yday = when.tm_yday
            time_obj.tm_isdst = when.tm_isdst
            time_obj.tm_gmtoff = when.tm_gmtoff
            time_obj.tm_zone = when.tm_zone
        else:
            time_obj = TIME()
            when = value.timetuple()
            time_obj.tm_sec = when.tm_sec
            time_obj.tm_min = when.tm_min
            time_obj.tm_hour = when.tm_hour
            time_obj.tm_mday = when.tm_mday
            time_obj.tm_mon = when.tm_mon
            time_obj.tm_year = when.tm_year
            time_obj.tm_wday = when.tm_wday
            time_obj.tm_yday = when.tm_yday
            time_obj.tm_isdst = when.tm_isdst
            time_obj.tm_gmtoff = when.tm_gmtoff
            time_obj.tm_zone = when.tm_zone
            self.value = time_obj
            setattr(obj._wrapped.contents, self.name, pointer(time_obj))


class JobTemplate:
    """A JobTemplate is both how to specify a job and how to search for jobs.
    """
    def __init__(self):
        self._wrapped = DRMAA_LIB.drmaa2_jtemplate_create()

    remoteCommand = DRMAA2String("remoteCommand")
    args = DRMAA2StringList("args", ListType.stringlist)
    submitAsHold = DRMAA2Bool("submitAsHold")
    rerunnable = DRMAA2Bool("rerunnable")
    jobEnvironment = DRMAA2Dict("jobEnvironment")
    workingDirectory = DRMAA2String("workingDirectory")
    jobCategory = DRMAA2String("jobCategory")
    email = DRMAA2StringList("email", ListType.stringlist)
    emailOnStarted = DRMAA2Bool("emailOnStarted")
    emailOnTerminated = DRMAA2Bool("emailOnTerminated")
    jobName = DRMAA2String("jobName")
    inputPath = DRMAA2String("inputPath")
    outputPath = DRMAA2String("outputPath")
    errorPath = DRMAA2String("errorPath")
    joinFiles = DRMAA2Bool("joinFiles")
    reservationId = DRMAA2String("reservationId")
    queueName = DRMAA2String("queueName")
    minSlots = DRMAA2LongLong("minSlots")
    maxSlots = DRMAA2LongLong("maxSlots")
    priority = DRMAA2LongLong("priority")
    candidateMachines = DRMAA2StringList("candidateMachines",
                                         ListType.stringlist)
    minPhysMemory = DRMAA2LongLong("minPhysMemory")
    machineOS = DRMAA2Enum("machineOS", OS)
    machineArch = DRMAA2Enum("machineArch", CPU)
    startTime = DRMAA2Time("startTime")
    deadlineTime = DRMAA2Time("deadlineTime")
    stageInFiles = DRMAA2Dict("stageInFiles")
    stageOutFiles = DRMAA2Dict("stageOutFiles")
    resourceLimits = DRMAA2Dict("resourceLimits")
    accountingId = DRMAA2Dict("accountingId")
    pe = DRMAA2Dict("uge_jt_pe")


    def as_structure(self):
        return self._wrapped


class JobSession:
    def __init__(self, name=None, contact=None):
        """The IDL description says this should have a contact name,
        but it isn't supported. UGE always makes the contact your
        user name."""
        name = name or uuid4().hex
        LOGGER.debug("Creating JobSession {}".format(name))
        contact_str = contact.encode() if contact else c_char_p()
        self._session = DRMAA_LIB.drmaa2_create_jsession(
            name.encode(), contact_str
        )
        if not self._session:
            raise RuntimeError(last_error())
        self.name = name

    @classmethod
    def from_existing(cls, name):
        """If user tangkend made JobSession crunch, then
        the job would be listed here as tangkend@crunch."""
        session = DRMAA_LIB.drmaa2_open_jsession(name.encode())
        if not session:
            raise RuntimeError(last_error())
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
            DRMAA_LIB.drmaa2_list_free(byref(c_void_p(name_list)))
        else:
            pass  # Nothing to return.
        return session_names

    def close(self):
        """A session must be closed to relinquish resources."""
        LOGGER.debug("close JobSession")
        CheckError(DRMAA_LIB.drmaa2_close_jsession(self._session))

    def destroy(self):
        """Destroying a session removes it from the scheduler's memory."""
        LOGGER.debug("Destroying {}".format(self.name))
        JobSession.destroy_named(self.name)

    @staticmethod
    def destroy_named(name):
        """Destroy a session by name, removing it from the
        scheduler's memory."""
        LOGGER.debug("Destroying {}".format(name))
        CheckError(DRMAA_LIB.drmaa2_destroy_jsession(
            name.encode()))

    def free(self):
        """This frees allocated free store to hold the session.
        Call this after closing the session."""
        LOGGER.debug("free JobSession")
        DRMAA_LIB.drmaa2_jsession_free(pointer(self._session))  # void

    @property
    def contact(self):
        contact_str = DRMAA_LIB.drmaa2_jsession_get_contact(self._session)
        if contact_str:
            return contact_str.decode()
        else:
            return None
