"""
This uses the native Python module, ctypes, to wrap the DRMAA2
library. It provides a bare-bones interface to every function in
the library.

You need two things to understand this file.
The OGF spec is GFD.194.pdf at
https://www.ogf.org/ogf/doku.php/documents/documents.
Find the drmaa2.h header file for UGE.
"""
import ctypes
import ctypes.util
from ctypes import c_char_p, c_void_p, c_long, c_int, c_longlong, c_float
from ctypes import POINTER, CFUNCTYPE, Structure, pointer, cast
from enum import Enum
import os
from pathlib import Path
import logging
import warnings


LOGGER = logging.getLogger("drmaa2.interface")
DRMAA_LIB = None


drmaa2_time = c_longlong


class Bool(Enum):
    """Boolean from drmaa2.h"""
    false = 0
    "False is 0"
    true = 1
    "True is 1"


class Capability(Enum):
    """Capabilities of the DRMAA implementation from drmaa2.h"""
    unset_capability = -1
    advance_reservation = 0
    reserve_slots = 1
    callback = 2
    bulk_jobs_maxparallel = 3
    jt_email = 4
    jt_staging = 5
    jt_deadline = 6
    jt_maxslots = 7
    jt_accountingid = 8
    rt_startnow = 9
    rt_duration = 10
    rt_machineos = 11
    rt_machinearch = 12


class CPU(Enum):
    """CPU types"""
    unset = -1
    OTHER = 0
    "Some other architecture"
    ALPHA = 1
    "Alpha"
    ARM = 2
    "ARM processor"
    ARM64 = 3
    "ARM64 processor"
    CELL = 4
    "Cell"
    PARISC = 5
    "Parisc"
    PARISC_64 = 6
    "Parisc_64"
    X86 = 7
    "x86"
    X64 = 8
    "x64"
    IA64 = 9
    "Intel Itanium"
    MIPS = 10
    "MIPS"
    MIPS64 = 11
    "MIPS64"
    PPC = 12
    "PowerPC"
    PPC64 = 13
    "PowerPC 64"
    SPARC = 14
    "SPARC"
    SPARC64 = 15
    "SPARC64"


class Error(Enum):
    """List of errors returned as drmaa2_error."""
    unset = -1
    success = 0
    denied_by_drms = 1
    drm_communication = 2
    try_later = 3
    session_management = 4
    timeout = 5
    internal = 6
    invalid_argument = 7
    invalid_session = 8
    invalid_state = 9
    out_of_resource = 10
    unsupported_attribute = 11
    unsupported_operation = 12
    implementation_specific = 13
    last_error = 14


class Event(Enum):
    """Used by callbacks to determine type of event in DRMAA."""
    unset = -1
    new_state = 0
    "Job is in a new state"
    migrated = 1
    "Job migrated to a new machine."
    attribute_change = 2
    "A job attribute was altered."


class ListType(Enum):
    """
    The DRMAA2 API defines a list of void pointers. This enum tells
    you which kinds of items are in the list.
    """
    unset = -1
    stringlist = 0
    joblist = 1
    queueinfolist = 2
    machineinfolist = 3
    slotinfolist = 4
    reservationlist = 5


class OS(Enum):
    """Operating system type."""
    unset = -1
    OTHER = 0
    "Some other operating system"
    AIX = 1
    "AIX"
    BSD = 2
    "BSD"
    LINUX = 3
    "Linux"
    HPUX = 4
    "HPUX"
    IRIX = 5
    "IRIX"
    MACOS = 6
    "MacOS"
    SUNOS = 7
    "SunOS"
    TRU64 = 8
    "Tru64"
    UNIXWARE = 9
    "Unixware"
    WIN = 10
    "Windows"
    WINNT = 11
    "WindowsNT"


class JState(Enum):
    """All job states."""
    unset = -1
    undetermined = 0
    "Undetermined"
    queued = 1
    "Queued"
    queued_held = 2
    "Queued but held in the queue"
    running = 3
    "Running"
    suspended = 4
    "Suspended"
    requeued = 5
    "Requeued"
    requeued_held = 6
    "Requeued and held"
    done = 7
    "Done"
    failed = 8
    "Failed"


enum_type = c_int
drmaa2_bool = enum_type
drmaa2_capability = enum_type
drmaa2_cpu = enum_type
drmaa2_error = enum_type
drmaa2_event = enum_type
drmaa2_listtype = enum_type
drmaa2_os = enum_type
drmaa2_jstate = enum_type


class drmaa2_string(c_char_p):
    """Making this a subclass disables automatic creation of the string.
    If ctypes converts the char* to a string, then it isn't possible
    to call drmaa2_string_free to free the value. Use the resulting
    string with::

       return return_str(DRMAA2_LIB.drmaa2_get_name(jsession))
    """
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other.encode()
        else:
            return self.value == other.value

    def __ne__(self, other):
        if isinstance(other, str):
            return self.value != other.encode()
        else:
            return self.value != other.value


def return_str(returned_from_drmaa2_call):
    """Retrieves a string and frees memory associated with the pointer.

    Why is the ctypes usual method not good enough? It doesn't free
    memory automatically, so wrapping a function like char* get_name()
    will lose the char*.
    """
    LOGGER.debug("enter return_str")
    result = returned_from_drmaa2_call.value
    DRMAA_LIB.drmaa2_string_free(pointer(returned_from_drmaa2_call))
    LOGGER.debug("leave return_str {}".format(result))
    if result:
        return result.decode()
    else:
        return None


drmaa2_list_s = c_void_p
drmaa2_list = drmaa2_list_s
drmaa2_string_list = drmaa2_list_s
drmaa2_j_list = drmaa2_list_s
drmaa2_queueinfo_list = drmaa2_list_s
drmaa2_machineinfo_list = drmaa2_list_s
drmaa2_slotinfo_list = drmaa2_list_s
drmaa2_r_list = drmaa2_list_s
DRMAA2_LIST_ENTRYFREE = CFUNCTYPE(None, POINTER(c_void_p))

drmaa2_dict = c_void_p
DRMAA2_DICT_ENTRYFREE = CFUNCTYPE(None,
                                  POINTER(c_char_p), POINTER(c_char_p))

# The following can be read, in order, from drmaa2.h,
# provided with the Univa Grid Engine implementation.
HOME_DIR = "$DRMAA2_HOME_DIR$"
WORKING_DIR = "$DRMAA2_WORKING_DIR$"
PARAMETRIC_INDEX = "$DRMAA2_INDEX$"

ZERO_TIME = drmaa2_time(0)
INFINITE_TIME = drmaa2_time(-1)
NOW = drmaa2_time(-2)


class Times(Enum):
    """If a function accepts a time parameter, these magic
    times correspond to ZERO time, INFINITE time, or NOW."""
    unset = -3
    zero = 0
    "Don't wait for any length of time."
    infinite = -1
    "Wait forever."
    now = -2
    "Do it now."


UNSET_BOOL = 0
UNSET_CALLBACK = c_void_p(0)
UNSET_DICT = c_void_p(0)
UNSET_ENUM = -1
UNSET_LIST = c_void_p(0)
UNSET_NUM = -1
UNSET_STRING = drmaa2_string()
UNSET_TIME = drmaa2_time(-3)
UNSET_JINFO = c_void_p(0)
UNSET_VERSION = c_void_p(0)


class ResourceLimits(Enum):
    """Strings that define resource limits."""
    core_file_size = "CORE_FILE_SIZE"
    "Maximum size for a core file."
    cpu_time = "CPU_TIME"
    "Max CPU time"
    data_size = "DATA_SIZE"
    "Max size of data segment?"
    file_size = "FILE_SIZE"
    "Maximum file size to write."
    open_files = "OPEN_FILES"
    "Maximum number of open files."
    stack_size = "STACK_SIZE"
    "Maximum size of process stack."
    virtual_memory = "VIRTUAL_MEMORY"
    "Limit on the virtual memory."
    wallclock_time = "WALLCLOCK_TIME"
    "Total wallclock time process can spend."


libc_name = ctypes.util.find_library("c")
libc = ctypes.CDLL(libc_name)
libc.memcmp.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t)


class CompareStructure(Structure):
    def __eq__(self, other):
        same = True
        for (attr_name, _) in self._fields_:
            a, b = getattr(self, attr_name), getattr(other, attr_name)
            if isinstance(a, ctypes.Array):
                if a[:] != b[:]:
                    same = False
                # or still True
            elif a != b:
                same = False
            # else still True
        return same

    def __ne__(self, other):
        return not self.__eq__(other)


class DRMAA2_JINFO(CompareStructure):
    _fields_ = [("jobId", drmaa2_string),
                ("exitStatus", c_int),
                ("terminatingSignal", drmaa2_string),
                ("annotation", drmaa2_string),
                ("jobState", drmaa2_jstate),
                ("jobSubState", drmaa2_string),
                ("allocatedMachines", drmaa2_string_list),
                ("submissionMachine", drmaa2_string),
                ("jobOwner", drmaa2_string),
                ("slots", c_longlong),
                ("queueName", drmaa2_string),
                ("wallclockTime", drmaa2_time),
                ("cpuTime", c_longlong),
                ("submissionTime", drmaa2_time),
                ("dispatchTime", drmaa2_time),
                ("finishTime", drmaa2_time),
                ("implementationSpecific", c_void_p)]


class DRMAA2_SLOTINFO(CompareStructure):
    _fields_ = [("machineName", drmaa2_string),
                ("slots", c_longlong)]


class DRMAA2_RINFO(CompareStructure):
    _fields_ = [("reservationId", drmaa2_string),
                ("reservationName", drmaa2_string),
                ("reservedStartTime", drmaa2_time),
                ("reservedEndTime", drmaa2_time),
                ("usersACL", drmaa2_string_list),
                ("reservedSlots", c_longlong),
                ("reservedMachines", drmaa2_slotinfo_list),
                ("implementationSpecific", c_void_p)]


# For UGE
class JTImplementationSpecific(CompareStructure):
    _fields_ = [("pe", drmaa2_string)]


class DRMAA2_JTEMPLATE(CompareStructure):
    _fields_ = [("remoteCommand", drmaa2_string),
                ("args", drmaa2_string_list),
                ("submitAsHold", drmaa2_bool),
                ("rerunnable", drmaa2_bool),
                ("jobEnvironment", drmaa2_dict),
                ("workingDirectory", drmaa2_string),
                ("jobCategory", drmaa2_string),
                ("email", drmaa2_string_list),
                ("emailOnStarted", drmaa2_bool),
                ("emailOnTerminated", drmaa2_bool),
                ("jobName", drmaa2_string),
                ("inputPath", drmaa2_string),
                ("outputPath", drmaa2_string),
                ("errorPath", drmaa2_string),
                ("joinFiles", drmaa2_bool),
                ("reservationId", drmaa2_string),
                ("queueName", drmaa2_string),
                ("minSlots", c_longlong),
                ("maxSlots", c_longlong),
                ("priority", c_longlong),
                ("candidateMachines", drmaa2_string_list),
                ("minPhysMemory", c_longlong),
                ("machineOS", drmaa2_os),
                ("machineArch", drmaa2_cpu),
                ("startTime", drmaa2_time),
                ("deadlineTime", drmaa2_time),
                ("stageInFiles", drmaa2_dict),
                ("stageOutFiles", drmaa2_dict),
                ("resourceLimits", drmaa2_dict),
                ("accountingId", drmaa2_string),
                ("implementationSpecific", c_void_p)]


class DRMAA2_RTEMPLATE(CompareStructure):
    _fields_ = [("reservationName", drmaa2_string),
                ("startTime", drmaa2_time),
                ("endTime", drmaa2_time),
                ("duration", drmaa2_time),
                ("minSlots", c_longlong),
                ("maxSlots", c_longlong),
                ("jobCategory", drmaa2_string),
                ("usersACL", drmaa2_string_list),
                ("candidateMachines", drmaa2_string_list),
                ("minPhysMemory", c_longlong),
                ("machineOS", drmaa2_os),
                ("machineArch", drmaa2_cpu),
                ("implementationSpecific", c_void_p)]


class DRMAA2_NOTIFICATION(CompareStructure):
    _fields_ = [("event", drmaa2_event),
                ("jobId", drmaa2_string),
                ("sessionName", drmaa2_string),
                ("jobState", drmaa2_jstate)]


class DRMAA2_QUEUEINFO(CompareStructure):
    _fields_ = [("name", drmaa2_string),
                ("implementationSpecific", c_void_p)]


class DRMAA2_VERSION(CompareStructure):
    _fields_ = [("major", drmaa2_string),
                ("minor", drmaa2_string)]


class DRMAA2_MACHINEINFO(CompareStructure):
    _fields_ = [("name", drmaa2_string),
                ("available", drmaa2_bool),
                ("sockets", c_longlong),
                ("coresPerSocket", c_longlong),
                ("threadsPerCore", c_longlong),
                ("load", c_float),
                ("physMemory", c_longlong),
                ("virtMemory", c_longlong),
                ("machineArch", drmaa2_cpu),
                ("machineOSVersion", DRMAA2_VERSION),
                ("machineOS", drmaa2_os),
                ("implementationSpecific", c_void_p)]


DRMAA2_CALLBACK = CFUNCTYPE(None, POINTER(DRMAA2_NOTIFICATION))


drmaa2_j = c_void_p
drmaa2_jarray = c_void_p
drmaa2_jsession = c_void_p
drmaa2_msession = c_void_p

# class DRMAA2_J(CompareStructure):
#     """UGE-specific, so we wrap it without the fields."""
#     _fields_ = [("id", drmaa2_string),
#                 ("sessionName", drmaa2_string)]
#
#
# # UGE-specific
# class DRMAA2_JARRAY(CompareStructure):
#     _fields_ = [("id", drmaa2_string),
#                 ("jobList", drmaa2_j_list),
#                 ("sessionName", drmaa2_string)]
#
#
# # UGE-specific
# class DRMAA2_JSESSION(CompareStructure):
#     _fields_ = [("contact", drmaa2_string),
#                 ("name", drmaa2_string)]
#
#
# # UGE-specific
# class DRMAA2_MSESSION(CompareStructure):
#     _fields_ = [("name", drmaa2_string)]



# UGE-specific, and I can't find these definitions, so they will be opaque.
drmaa2_rsession = c_void_p
drmaa2_r = c_void_p


def load_drmaa_library():
    global DRMAA_LIB
    if DRMAA_LIB:
        LOGGER.debug("Already have a DRMAA_LIB. Return it.")
        return DRMAA_LIB
    try:
        SGE_ROOT = Path(os.environ["SGE_ROOT"])
        drmaa2_name = SGE_ROOT / "lib/lx-amd64" / "libdrmaa2.so"
    except KeyError:
        drmaa2_name = "libdrmaa2.so"
        LOGGER.debug("There is no SGE_ROOT. Try the bare filename.")
    try:
        DRMAA_LIB = ctypes.cdll.LoadLibrary(str(drmaa2_name))
    except OSError:
        LOGGER.debug("Failed to load the library.")
        warnings.warn("Cannot open the DRMAA_LIB for DRMAA")
        return None
    LOGGER.debug("Initializing DRMAA2")

    # The argument type is a c_void_p which takes any pointer.
    # Note well! Most free functions accept a pointer as argument.
    # This one accepts a pointer to a pointer. Fail to dereference,
    # and segmentation faults will result.
    DRMAA_LIB.drmaa2_string_free.restype = None
    DRMAA_LIB.drmaa2_string_free.argtypes = [POINTER(drmaa2_string)]

    DRMAA_LIB.drmaa2_list_create.restype = drmaa2_list
    DRMAA_LIB.drmaa2_list_create.argtypes =\
            [drmaa2_listtype, DRMAA2_LIST_ENTRYFREE]
    DRMAA_LIB.drmaa2_list_free.restype = None
    DRMAA_LIB.drmaa2_list_free.argtypes = [POINTER(drmaa2_list)]
    DRMAA_LIB.drmaa2_list_get.restype = c_void_p
    DRMAA_LIB.drmaa2_list_get.argtypes = [drmaa2_list, c_long]
    DRMAA_LIB.drmaa2_list_add.restype = drmaa2_error
    DRMAA_LIB.drmaa2_list_add.argtypes = [drmaa2_list, c_void_p]
    DRMAA_LIB.drmaa2_list_del.restype = drmaa2_error
    DRMAA_LIB.drmaa2_list_del.argtypes = [drmaa2_list, c_long]
    DRMAA_LIB.drmaa2_list_size.restype = c_long
    DRMAA_LIB.drmaa2_list_size.argtypes = [drmaa2_list]

    DRMAA_LIB.drmaa2_lasterror.restype = drmaa2_error
    DRMAA_LIB.drmaa2_lasterror.argtypes = []
    DRMAA_LIB.drmaa2_lasterror_text.restype = drmaa2_string
    DRMAA_LIB.drmaa2_lasterror_text.argtypes = []

    # Nonstandard
    DRMAA_LIB.uge_drmaa2_list_free_root.restype = None
    DRMAA_LIB.uge_drmaa2_list_free_root.argtypes = [POINTER(drmaa2_list)]
    # Nonstandard
    DRMAA_LIB.uge_drmaa2_list_set.restype = drmaa2_error
    DRMAA_LIB.uge_drmaa2_list_set.argtypes = [drmaa2_list, c_long, c_void_p]

    DRMAA_LIB.drmaa2_dict_create.restype = drmaa2_dict
    DRMAA_LIB.drmaa2_dict_create.argtypes = [DRMAA2_DICT_ENTRYFREE]
    DRMAA_LIB.drmaa2_dict_free.restype = None
    DRMAA_LIB.drmaa2_dict_free.argtypes = [POINTER(drmaa2_dict)]
    DRMAA_LIB.drmaa2_dict_list.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_dict_list.argtypes = [drmaa2_dict]
    DRMAA_LIB.drmaa2_dict_has.restype = drmaa2_bool
    DRMAA_LIB.drmaa2_dict_has.argtypes = [drmaa2_dict, c_char_p]
    DRMAA_LIB.drmaa2_dict_get.restype = c_char_p
    DRMAA_LIB.drmaa2_dict_get.argtypes = [drmaa2_dict, c_char_p]
    DRMAA_LIB.drmaa2_dict_del.restype = drmaa2_error
    DRMAA_LIB.drmaa2_dict_del.argtypes = [drmaa2_dict, c_char_p]
    DRMAA_LIB.drmaa2_dict_set.restype = drmaa2_error
    DRMAA_LIB.drmaa2_dict_set.argtypes = [drmaa2_dict, c_char_p]

    DRMAA_LIB.drmaa2_jinfo_create.restype = POINTER(DRMAA2_JINFO)
    DRMAA_LIB.drmaa2_jinfo_create.argtypes = []
    DRMAA_LIB.drmaa2_jinfo_free.restype = None
    DRMAA_LIB.drmaa2_jinfo_free.argtypes = [c_void_p]

    DRMAA_LIB.drmaa2_slotinfo_free.restype = None
    DRMAA_LIB.drmaa2_slotinfo_free.argtypes = [
        POINTER(POINTER(DRMAA2_SLOTINFO))]

    DRMAA_LIB.drmaa2_rinfo_free.restype = None
    DRMAA_LIB.drmaa2_rinfo_free.argtypes = [POINTER(POINTER(DRMAA2_RINFO))]

    DRMAA_LIB.drmaa2_jtemplate_create.restype = POINTER(DRMAA2_JTEMPLATE)
    DRMAA_LIB.drmaa2_jtemplate_create.argtypes = []
    DRMAA_LIB.drmaa2_jtemplate_free.restype = None
    DRMAA_LIB.drmaa2_jtemplate_free.argtypes = [
        POINTER(POINTER(DRMAA2_JTEMPLATE))]

    DRMAA_LIB.drmaa2_rtemplate_create.restype = POINTER(DRMAA2_RTEMPLATE)
    DRMAA_LIB.drmaa2_rtemplate_create.argtypes = []
    DRMAA_LIB.drmaa2_rtemplate_free.restype = None
    DRMAA_LIB.drmaa2_rtemplate_free.argtypes = [
        POINTER(POINTER(DRMAA2_RTEMPLATE))]

    DRMAA_LIB.drmaa2_notification_free.restype = None
    DRMAA_LIB.drmaa2_notification_free.argtypes = [
        POINTER(POINTER(DRMAA2_NOTIFICATION))]

    DRMAA_LIB.drmaa2_queueinfo_free.restype = None
    DRMAA_LIB.drmaa2_queueinfo_free.argtypes = [
        POINTER(POINTER(DRMAA2_QUEUEINFO))]

    DRMAA_LIB.drmaa2_version_free.restype = None
    DRMAA_LIB.drmaa2_version_free.argtypes = [POINTER(POINTER(DRMAA2_VERSION))]

    DRMAA_LIB.drmaa2_machineinfo_free.restype = None
    DRMAA_LIB.drmaa2_machineinfo_free.argtypes = [
        POINTER(POINTER(DRMAA2_MACHINEINFO))]

    # These are dynamic queries to discover what other members
    # these structs have on this platform.
    DRMAA_LIB.drmaa2_jtemplate_impl_spec.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_jtemplate_impl_spec.argtypes = []
    DRMAA_LIB.drmaa2_jinfo_impl_spec.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_jinfo_impl_spec.argtypes = []
    DRMAA_LIB.drmaa2_rtemplate_impl_spec.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_rtemplate_impl_spec.argtypes = []
    DRMAA_LIB.drmaa2_rinfo_impl_spec.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_rinfo_impl_spec.argtypes = []
    DRMAA_LIB.drmaa2_queueinfo_impl_spec.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_queueinfo_impl_spec.argtypes = []
    DRMAA_LIB.drmaa2_machineinfo_impl_spec.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_machineinfo_impl_spec.argtypes = []
    DRMAA_LIB.drmaa2_notification_impl_spec.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_notification_impl_spec.argtypes = []

    DRMAA_LIB.drmaa2_get_instance_value.restype = drmaa2_string
    DRMAA_LIB.drmaa2_get_instance_value.argtypes = [c_void_p, c_char_p]
    DRMAA_LIB.drmaa2_describe_attribute.restype = drmaa2_string
    DRMAA_LIB.drmaa2_describe_attribute.argtypes = [c_void_p, c_char_p]
    DRMAA_LIB.drmaa2_set_instance_value.restype = drmaa2_error
    DRMAA_LIB.drmaa2_set_instance_value.argtypes = [c_void_p,
                                                    c_char_p, c_char_p]

    DRMAA_LIB.drmaa2_jsession_free.restype = None
    DRMAA_LIB.drmaa2_jsession_free.argtypes = [c_void_p]
    DRMAA_LIB.drmaa2_rsession_free.restype = None
    DRMAA_LIB.drmaa2_rsession_free.argtypes = [
        POINTER(drmaa2_rsession)]
    DRMAA_LIB.drmaa2_msession_free.restype = None
    DRMAA_LIB.drmaa2_msession_free.argtypes = [
        POINTER(drmaa2_msession)]
    DRMAA_LIB.drmaa2_j_free.restype = None
    DRMAA_LIB.drmaa2_j_free.argtypes = [c_void_p]
    DRMAA_LIB.drmaa2_jarray_free.restype = None
    DRMAA_LIB.drmaa2_jarray_free.argtypes = [c_void_p]
    # These are in the header drmaa2.h but not libdrmaa2.so.
    # DRMAA_LIB.drmaa2_r_free.restype = None
    # DRMAA_LIB.drmaa2_r_free.argtypes = [POINTER(drmaa2_r)]

    DRMAA_LIB.drmaa2_rsession_get_contact.restype = drmaa2_string
    DRMAA_LIB.drmaa2_rsession_get_contact.argtypes = [drmaa2_rsession]
    DRMAA_LIB.drmaa2_rsession_get_session_name.restype = drmaa2_string
    DRMAA_LIB.drmaa2_rsession_get_session_name.argtypes = [
        drmaa2_rsession]
    DRMAA_LIB.drmaa2_rsession_get_reservation.restype = drmaa2_r
    DRMAA_LIB.drmaa2_rsession_get_reservation.argtypes = [
        drmaa2_rsession]
    DRMAA_LIB.drmaa2_rsession_request_reservation.restype = drmaa2_r
    DRMAA_LIB.drmaa2_rsession_request_reservation.argtypes = [
        drmaa2_rsession, POINTER(DRMAA2_RTEMPLATE)
    ]
    DRMAA_LIB.drmaa2_rsession_get_reservations.restype = drmaa2_r_list
    DRMAA_LIB.drmaa2_rsession_get_reservations.argtypes = [
        drmaa2_rsession]

    DRMAA_LIB.drmaa2_r_get_id.restype = drmaa2_string
    DRMAA_LIB.drmaa2_r_get_id.argtypes = [drmaa2_r]
    DRMAA_LIB.drmaa2_r_get_session_name.restype = drmaa2_string
    DRMAA_LIB.drmaa2_r_get_session_name.argtypes = [drmaa2_r]
    DRMAA_LIB.drmaa2_r_get_reservation_template.restype = \
        POINTER(DRMAA2_RTEMPLATE)
    DRMAA_LIB.drmaa2_r_get_reservation_template.argtypes = [drmaa2_r]
    DRMAA_LIB.drmaa2_r_get_info.restype = POINTER(DRMAA2_RINFO)
    DRMAA_LIB.drmaa2_r_get_info.argtypes = [drmaa2_r]
    DRMAA_LIB.drmaa2_r_terminate.restype = drmaa2_error
    DRMAA_LIB.drmaa2_r_terminate.argtypes = [drmaa2_r]

    DRMAA_LIB.drmaa2_jarray_get_id.restype = drmaa2_string
    DRMAA_LIB.drmaa2_jarray_get_id.argtypes = [drmaa2_jarray]
    DRMAA_LIB.drmaa2_jarray_get_jobs.restype = drmaa2_j_list
    DRMAA_LIB.drmaa2_jarray_get_jobs.argtypes = [drmaa2_jarray]
    DRMAA_LIB.drmaa2_jarray_get_session_name.restype = drmaa2_string
    DRMAA_LIB.drmaa2_jarray_get_session_name.argtypes = [drmaa2_jarray]
    DRMAA_LIB.drmaa2_jarray_get_jtemplate.restype = POINTER(DRMAA2_JTEMPLATE)
    DRMAA_LIB.drmaa2_jarray_get_jtemplate.argtypes = [drmaa2_jarray]
    DRMAA_LIB.drmaa2_jarray_suspend.restype = drmaa2_error
    DRMAA_LIB.drmaa2_jarray_suspend.argtypes = [drmaa2_jarray]
    DRMAA_LIB.drmaa2_jarray_resume.restype = drmaa2_error
    DRMAA_LIB.drmaa2_jarray_resume.argtypes = [drmaa2_jarray]
    DRMAA_LIB.drmaa2_jarray_hold.restype = drmaa2_error
    DRMAA_LIB.drmaa2_jarray_hold.argtypes = [drmaa2_jarray]
    DRMAA_LIB.drmaa2_jarray_release.restype = drmaa2_error
    DRMAA_LIB.drmaa2_jarray_release.argtypes = [drmaa2_jarray]
    DRMAA_LIB.drmaa2_jarray_terminate.restype = drmaa2_error
    DRMAA_LIB.drmaa2_jarray_terminate.argtypes = [drmaa2_jarray]

    DRMAA_LIB.drmaa2_jsession_get_contact.restype = drmaa2_string
    DRMAA_LIB.drmaa2_jsession_get_contact.argtypes = [
        drmaa2_jsession]
    DRMAA_LIB.drmaa2_jsession_get_session_name.restype = drmaa2_string
    DRMAA_LIB.drmaa2_jsession_get_session_name.argtypes = [
        drmaa2_jsession]
    DRMAA_LIB.drmaa2_jsession_get_job_categories.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_jsession_get_job_categories.argtypes = [
        drmaa2_jsession]
    DRMAA_LIB.drmaa2_jsession_get_jobs.restype = drmaa2_j_list
    DRMAA_LIB.drmaa2_jsession_get_jobs.argtypes = [drmaa2_jsession,
                                                   POINTER(DRMAA2_JINFO)]
    DRMAA_LIB.drmaa2_jsession_get_job_array.restype = drmaa2_jarray
    DRMAA_LIB.drmaa2_jsession_get_job_array.argtypes = [
        drmaa2_jsession, drmaa2_string]
    DRMAA_LIB.drmaa2_jsession_run_job.restype = drmaa2_j
    DRMAA_LIB.drmaa2_jsession_run_job.argtypes = [drmaa2_jsession,
                                                  POINTER(DRMAA2_JTEMPLATE)]
    DRMAA_LIB.drmaa2_jsession_run_bulk_jobs.restype = drmaa2_jarray
    DRMAA_LIB.drmaa2_jsession_run_bulk_jobs.argtypes = [
        drmaa2_jsession, POINTER(DRMAA2_JTEMPLATE),
        c_longlong, c_longlong, c_longlong, c_longlong]
    DRMAA_LIB.drmaa2_jsession_wait_any_started.restype = drmaa2_j
    DRMAA_LIB.drmaa2_jsession_wait_any_started.argtypes = [
        drmaa2_jsession, drmaa2_j_list, drmaa2_time]
    DRMAA_LIB.drmaa2_jsession_wait_any_terminated.restype = drmaa2_j
    DRMAA_LIB.drmaa2_jsession_wait_any_terminated.argtypes = [
        drmaa2_jsession, drmaa2_j_list, drmaa2_time]
    DRMAA_LIB.drmaa2_j_suspend.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_suspend.argtypes = [drmaa2_j]
    DRMAA_LIB.drmaa2_j_resume.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_resume.argtypes = [drmaa2_j]
    DRMAA_LIB.drmaa2_j_release.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_release.argtypes = [drmaa2_j]
    DRMAA_LIB.drmaa2_j_terminate.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_terminate.argtypes = [drmaa2_j]
    DRMAA_LIB.drmaa2_j_reap.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_reap.argtypes = [drmaa2_j]
    DRMAA_LIB.drmaa2_j_get_id.restype = drmaa2_string
    DRMAA_LIB.drmaa2_j_get_id.argtypes = [drmaa2_j]
    DRMAA_LIB.drmaa2_j_get_jtemplate.restype = POINTER(DRMAA2_JTEMPLATE)
    DRMAA_LIB.drmaa2_j_get_jtemplate.argtypes = [drmaa2_j]
    DRMAA_LIB.drmaa2_j_get_state.restype = drmaa2_jstate
    DRMAA_LIB.drmaa2_j_get_state.argtypes = [drmaa2_j]
    DRMAA_LIB.drmaa2_j_get_info.restype = POINTER(DRMAA2_JINFO)
    DRMAA_LIB.drmaa2_j_get_info.argtypes = [drmaa2_j]
    DRMAA_LIB.drmaa2_j_wait_started.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_wait_started.argtypes = [drmaa2_j, drmaa2_time]
    DRMAA_LIB.drmaa2_j_wait_terminated.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_wait_terminated.argtypes = [drmaa2_j]

    DRMAA_LIB.drmaa2_msession_get_all_reservations.restype = drmaa2_r_list
    DRMAA_LIB.drmaa2_msession_get_all_reservations.argtypes = [
        drmaa2_msession]
    DRMAA_LIB.drmaa2_msession_get_all_jobs.restype = drmaa2_j_list
    DRMAA_LIB.drmaa2_msession_get_all_jobs.argtypes = [drmaa2_msession,
                                                       POINTER(DRMAA2_JINFO)]
    DRMAA_LIB.drmaa2_msession_get_all_queues.restype = drmaa2_queueinfo_list
    DRMAA_LIB.drmaa2_msession_get_all_queues.argtypes = [
        drmaa2_msession, drmaa2_string_list]
    DRMAA_LIB.drmaa2_msession_get_all_machines.restype = drmaa2_machineinfo_list
    DRMAA_LIB.drmaa2_msession_get_all_machines.argtypes = [
        drmaa2_msession, drmaa2_string_list]

    DRMAA_LIB.drmaa2_get_drms_name.restype = drmaa2_string
    DRMAA_LIB.drmaa2_get_drms_name.argtypes = []
    DRMAA_LIB.drmaa2_get_drms_version.restype = POINTER(DRMAA2_VERSION)
    DRMAA_LIB.drmaa2_get_drms_version.argtypes = []
    DRMAA_LIB.drmaa2_supports.restype = drmaa2_bool
    DRMAA_LIB.drmaa2_supports.argtypes = [drmaa2_capability]
    DRMAA_LIB.drmaa2_create_jsession.restype = drmaa2_jsession
    DRMAA_LIB.drmaa2_create_jsession.argtypes = [c_char_p, c_char_p]
    DRMAA_LIB.drmaa2_create_rsession.restype = drmaa2_rsession
    DRMAA_LIB.drmaa2_create_rsession.argtypes = [c_char_p, c_char_p]
    DRMAA_LIB.drmaa2_open_jsession.restype = drmaa2_jsession
    DRMAA_LIB.drmaa2_open_jsession.argtypes = [c_char_p]
    DRMAA_LIB.drmaa2_open_rsession.restype = drmaa2_rsession
    DRMAA_LIB.drmaa2_open_rsession.argtypes = [c_char_p]
    DRMAA_LIB.drmaa2_open_msession.restype = drmaa2_msession
    DRMAA_LIB.drmaa2_open_msession.argtypes = [c_char_p]
    DRMAA_LIB.drmaa2_close_jsession.restype = drmaa2_error
    DRMAA_LIB.drmaa2_close_jsession.argtypes = [drmaa2_jsession]
    DRMAA_LIB.drmaa2_close_rsession.restype = drmaa2_error
    DRMAA_LIB.drmaa2_close_rsession.argtypes = [drmaa2_rsession]
    DRMAA_LIB.drmaa2_close_msession.restype = drmaa2_error
    DRMAA_LIB.drmaa2_close_msession.argtypes = [drmaa2_msession]
    DRMAA_LIB.drmaa2_destroy_jsession.restype = drmaa2_error
    DRMAA_LIB.drmaa2_destroy_jsession.argtypes = [c_char_p]
    DRMAA_LIB.drmaa2_destroy_rsession.restype = drmaa2_error
    DRMAA_LIB.drmaa2_destroy_rsession.argtypes = [c_char_p]
    DRMAA_LIB.drmaa2_get_jsession_names.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_get_jsession_names.argtypes = []
    DRMAA_LIB.drmaa2_get_rsession_names.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_get_rsession_names.argtypes = []
    DRMAA_LIB.drmaa2_register_event_notification.restype = drmaa2_error
    DRMAA_LIB.drmaa2_register_event_notification.argtypes = [
        POINTER(DRMAA2_CALLBACK)]
    return DRMAA_LIB
