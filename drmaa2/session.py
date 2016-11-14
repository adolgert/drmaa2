"""
This creates classes around the Session interface of
the DRMAA2 library using the interface module to
provide access to the native library.
"""
import atexit
import collections
from collections.abc import Sequence
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


def check_errno():
    if last_errno() > 0:
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
        self.name = name.split(".")
        self.was_set = False

    def __get__(self, obj, type=None):
        if len(self.name) > 1:
            base = getattr(obj._wrapped.contents, self.name[0])
        else:
            base = obj._wrapped.contents
        wrapped_value = getattr(base, self.name[-1]).value
        if wrapped_value is None:  # Exclude case where it is "".
            return wrapped_value
        else:
            return wrapped_value.decode()

    def __set__(self, obj, value):
        if len(self.name) > 1:
            base = getattr(obj._wrapped.contents, self.name[0])
        else:
            base = obj._wrapped.contents
        wrapped_value = getattr(base, self.name[-1])
        if wrapped_value.value and not self.was_set:
            DRMAA_LIB.drmaa2_string_free(byref(wrapped_value))
        else:
            pass  # No need to free it if it's null.
        if value is not None:
            setattr(base, self.name[-1],
                    drmaa2_string(str(value).encode()))
            self.was_set = True
        else:
            setattr(base, self.name[-1], UNSET_STRING)

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


class StringStrategy:
    @staticmethod
    def from_void(void_ptr):
        """Makes a Python object which is a copy of the value."""
        return cast(void_ptr, drmaa2_string).value.decode()

    @staticmethod
    def to_void(name_str):
        """Sets up the Python object so that ctypes can convert it
        to be passed to the library. You have to keep a copy of this
        object around, meaning keep a reference to it within Python
        for the duration of its use in the library."""
        return name_str.encode()

    @staticmethod
    def compare_pointers(a, b):
        return void_to_str(a) == void_to_str(b)


class JobStrategy:
    @staticmethod
    def from_void(void_ptr):
        return JobStrategy.from_ptr(cast(void_ptr, POINTER(DRMAA2_J)))

    @staticmethod
    def from_ptr(void_ptr):
        j = cast(void_ptr, POINTER(DRMAA2_J))
        if j:
            c = j.contents
            return Job(c.id.value.decode(), c.sessionName.value.decode())
        else:
            return None

    @staticmethod
    def to_void(job):
        j = DRMAA2_J()
        j.id = job.id.encode()
        j.sessionName = job.sessionName.encode()
        return byref(j)

    @staticmethod
    def compare_pointers(a, b):
        return JobStrategy.from_void(a) == JobStrategy.from_void(b)
        # return libc.memcmp(a, b, ctypes.sizeof(DRMAA2_J))


def convert_string_list(string_list):
    python_list = list()
    if string_list:
        string_cnt = DRMAA_LIB.drmaa2_list_size(string_list)
        check_errno()
        for string_idx in range(string_cnt):
            void_p = DRMAA_LIB.drmaa2_list_get(string_list, string_idx)
            assert last_errno() < 1
            name = cast(void_p, drmaa2_string).value.decode()
            LOGGER.debug("{} at index {}".format(name, string_idx))
            python_list.append(name)

    return python_list


def convert_and_free_string_list(string_list):
    python_list = convert_string_list(string_list)
    if string_list:
        DRMAA_LIB.drmaa2_list_free(byref(c_void_p(string_list)))  # void
    return python_list


class DRMAA2List(Sequence):
    """A DRMAAList owns a DRMAA list of things."""

    translators = {
        ListType.stringlist: StringStrategy,
        ListType.joblist: JobStrategy
    }

    def __init__(self, python_entries, list_type=ListType.stringlist):
        """If a pointer is passed to this class, then this class
        is responsible for freeing that list pointer. If none is passed,
        then this class creates a list pointer."""
        self.list_type = self.hint_type(list_type)
        self.strategy = self.translators[self.list_type]
        self.list_ptr = DRMAA_LIB.drmaa2_list_create(
            self.list_type.value, DRMAA2_LIST_ENTRYFREE())
        self._pin = [self.strategy.to_void(x) for x in python_entries]
        for add_item in self._pin:
            CheckError(DRMAA_LIB.drmaa2_list_add(self.list_ptr, add_item))

    @staticmethod
    def hint_type(list_type):
        if isinstance(list_type, ListType):
            return list_type
        elif isinstance(list_type, str):
            return ListType[list_type]
        else:
            return ListType(list_type)

    @classmethod
    def from_existing(cls, list_ptr, list_type):
        obj = cls.__new__(cls)
        obj.list_ptr = list_ptr
        obj.list_type = obj.hint_type(list_type)
        obj.strategy = obj.translators[obj.list_type]
        return obj

    def __getitem__(self, item):
        if item >= self.__len__():
            raise IndexError()
        void_p = DRMAA_LIB.drmaa2_list_get(self.list_ptr, item)
        return self.strategy.from_void(void_p)

    def __len__(self):
        return DRMAA_LIB.drmaa2_list_size(self.list_ptr)

    def __del__(self):
        """This isn't called when you call del but when garbage collection
        happens."""
        if self.list_ptr:
            DRMAA_LIB.drmaa2_list_free(byref(c_void_p(self.list_ptr)))
            self.list_ptr = None

    def __eq__(self, other):
        """Compares two DRMAA2Lists"""
        self_cnt = self.__len__()
        other_cnt = other.__len__()
        if self_cnt != other_cnt:
            return False
        for cmp_idx in range(self_cnt):
            self_p = DRMAA_LIB.drmaa2_list_get(self.list_ptr, cmp_idx)
            other_p = DRMAA_LIB.drmaa2_list_get(other.list_ptr, cmp_idx)
            if not self.strategy.compare_pointers(self_p, other_p):
                return False
        return True

    @staticmethod
    def return_list(string_ptr, list_type):
        l_ptr = DRMAA2List.from_existing(string_ptr, list_type)
        l_py = list(l_ptr)
        l_ptr.__del__()
        return l_py


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


    def free(self):
        if self.allocated:
            DRMAA_LIB.drmaa2_list_free(byref(self.allocated))


def job_template_implementation_specific():
    string_list = DRMAA_LIB.drmaa2_jtemplate_impl_spec()
    return convert_and_free_string_list(string_list)


class DRMAA2JobList:
    def __init__(self, name):
        """Name is the name of the member of the instance.
        list_type is the ListType enum for this list.
        If there isn't a list, we make one, so we free it, too."""
        self.name = name
        self.list_type = ListType.joblist
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
                string_list.append(Job.from_existing(
                    cast(void_p, POINTER(DRMAA2_J))))
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
        when = getattr(obj._wrapped.contents, self.name)
        LOGGER.debug("time is {}".format(when))
        try:
            message = Times(when)
            if message == Times.unset:
                return None
            else:
                return message.name
        except ValueError:
            return datetime.datetime.fromtimestamp(when)

    def __set__(self, obj, value):
        LOGGER.debug("set time for {} to {}".format(self.name, value))
        if value is None:
            when = Times["unset"].value
        elif isinstance(value, str):
            when = Times[value].value
        else:
            when = int(value.timestamp())
        setattr(obj._wrapped.contents, self.name, when)


class JobTemplate:
    """A JobTemplate is both how to specify a job and how to search for jobs.
    """
    def __init__(self):
        self._wrapped = DRMAA_LIB.drmaa2_jtemplate_create()
        # self._extensible = Extensible(
        #     self, DRMAA_LIB.drmaa2_jtemplate_impl_spec)

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
    pe = DRMAA2String("implementationSpecific.pe")

    def as_structure(self):
        return self._wrapped

    # def __getattr__(self, name):
    #     return ext_get(self, name, DRMAA_LIB.drmaa2_jtemplate_impl_spec)
    #
    # def __setattr__(self, name, value):
    #     set_special = ext_set(
    #         self, name, value, DRMAA_LIB.drmaa2_jtemplate_impl_spec)
    #     if not set_special:
    #         self.__dict__[name] = value

    def implementation_specific(self):
        return implementation_specific(DRMAA_LIB.drmaa2_jtemplate_impl_spec)


def ext_get(parent, name, checker):
    if name in implementation_specific(checker):
        d_string = DRMAA_LIB.drmaa2_get_instance_value(
            cast(parent._wrapped, c_void_p),
            name.encode())
        # This can sometimes cast a spurious error that the value isn't
        # specified, even though the value is just currently unset.
        if last_errno() < 1:
            return return_str(d_string)
        else:
            raise DRMAA2Exception(last_error())
    else:
        raise AttributeError

def ext_set(parent, name, value, checker):
    if name in implementation_specific(checker):
        if value is None:
            value = "".encode()
        else:
            value = value.encode()
        DRMAA_LIB.drmaa2_set_instance_value(
            cast(parent._wrapped, c_void_p),
            name.encode(),
            value)
        check_errno()
        return True
    else:
        return False

def implementation_specific(checker):
    LOGGER.debug("enter implementation_specific {}".format(DRMAA_LIB))
    d_string = checker()
    return convert_and_free_string_list(d_string)


def describe(self, name):
    d_string = DRMAA_LIB.drmaa2_describe_attribute(
        cast(self.parent._wrapped, c_void_p), name.encode())
    return return_str(d_string)


Job = collections.namedtuple("Job", "id sessionName")


# class Job:
#     def __init__(self, id, sessionName):
#         """Use this to create a new job.
#
#         :param id str: The Job ID
#         :param session_name str: The name of the DRMAA job session."""
#         self._value = DRMAA2_J()
#         self._wrapped = pointer(self._value)
#         self.id = id
#         self.sessionName = sessionName
#
#     @classmethod
#     def from_existing(cls, job_struct):
#         obj = cls.__new__(cls)
#         obj._wrapped = job_struct
#         return obj
#
#     id = DRMAA2String("id")
#     sessionName = DRMAA2String("sessionName")
#
#     def __str__(self):
#         return "({}, {})".format(self.id, self.sessionName)
#
#     def __repr__(self):
#         return "Job({}, {})".format(self.id, self.sessionName)


class Notification:
    def __init__(self, notification_struct):
        self._wrapped = notification_struct

    event = DRMAA2Enum("event", Event)
    jobId = DRMAA2String("jobId")
    sessionName = DRMAA2String("sessionName")
    jobState = DRMAA2Enum("jobState", JState)


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

    def run(self, job_template):
        job = DRMAA_LIB.drmaa2_jsession_run_job(
            self._session, job_template._wrapped)
        if not job:
            raise RuntimeError(last_error)
        job_obj = JobStrategy.from_ptr(job)
        DRMAA_LIB.drmaa2_j_free(job)
        return job_obj

    def next_terminated(self, job_list, how_long):
        job_ptr = DRMAA_LIB.drmaa2_jsession_wait_any_terminated(
            self._session, job_list, how_long)


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
