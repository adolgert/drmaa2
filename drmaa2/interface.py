import ctypes
from ctypes import c_char_p, c_void_p, c_long, c_int, c_longlong, c_float
from ctypes import POINTER, CFUNCTYPE, Structure
from enum import Enum
import os
from pathlib import Path
import logging


LOGGER = logging.getLogger("drmaa2.interface")
DRMAA_LIB = None


class TIME(Structure):
    _fields_ = [("tm_sec", c_int),
                ("tm_min", c_int),
                ("tm_hour", c_int),
                ("tm_mday", c_int),
                ("tm_mon", c_int),
                ("tm_year", c_int),
                ("tm_wday", c_int),
                ("tm_yday", c_int),
                ("tm_isdst", c_int),
                ("tm_gmtoff", c_long),
                ("tm_zone", c_char_p)]


ZERO_TIME = TIME(tm_sec = 0)
INFINITE_TIME = TIME(tm_sec=-1)
NOW = TIME(tm_sec=-2)

UNSET_BOOL = 0
UNSET_CALLBACK = c_void_p(0)
UNSET_DICT = c_void_p(0)
UNSET_ENUM = -1
UNSET_LIST = c_void_p(0)
UNSET_NUM = -1
UNSET_STRING = c_void_p(0)
UNSET_TIME = TIME(tm_sec=-3)
UNSET_JINFO = c_void_p(0)
UNSET_VERSION = c_void_p(0)


class Bool(Enum):
    false = 0
    true = 1


class Capability(Enum):
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
    unset_cpu = -1
    other_cpu = 0
    alpha = 1
    arm = 2
    arm64 = 3
    cell = 4
    parisc = 5
    parisc_64 = 6
    x86 = 7
    x64 = 8
    ia64 = 9
    mips = 10
    mips64 = 11
    ppc = 12
    ppc64 = 13
    sparc = 14
    sparc64 = 15


class Error(Enum):
    unset_error = -1
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
    unset_event = -1
    new_state = 0
    migrated = 1
    attribute_change = 2


class ListType(Enum):
    unset_listtype = -1
    stringlist = 0
    joblist = 1
    queueinfolist = 2
    machineinfolist = 3
    slotinfolist = 4
    resrevationlist = 5


class OS(Enum):
    unset_os = -1
    other_os = 0
    aix = 1
    bsd = 2
    linux = 3
    hpux = 4
    irix = 5
    macos = 6
    sunos = 7
    tru64 = 8
    unixware = 9
    win = 10
    winnt = 11


class JState(Enum):
    unset_jstate = -1
    undetermined = 0
    queued = 1
    queued_held = 2
    running = 3
    suspended = 4
    requeued = 5
    requeued_held = 6
    done = 7
    failed = 8


enum_type = c_int
drmaa2_bool = enum_type
drmaa2_capability = enum_type
drmaa2_cpu = enum_type
drmaa2_error = enum_type
drmaa2_event = enum_type
drmaa2_listtype = enum_type
drmaa2_os = enum_type
drmaa2_jstate = enum_type

drmaa2_string = c_char_p

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


class DRMAA2_JINFO(Structure):
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
                ("wallclockTime", POINTER(TIME)),
                ("cpuTime", c_longlong),
                ("submissionTime", POINTER(TIME)),
                ("dispatchTime", POINTER(TIME)),
                ("finishTime", POINTER(TIME)),
                ("implementationSpecific", c_void_p)]


class DRMAA2_SLOTINFO(Structure):
    _fields_ = [("machineName", drmaa2_string),
                ("slots", c_longlong)]


class DRMAA2_RINFO(Structure):
    _fields_ = [("reservationId", drmaa2_string),
                ("reservationName", drmaa2_string),
                ("reservedStartTime", POINTER(TIME)),
                ("reservedEndTime", POINTER(TIME)),
                ("usersACL", drmaa2_string_list),
                ("reservedSlots", c_longlong),
                ("reservedMachines", drmaa2_slotinfo_list),
                ("implementationSpecific", c_void_p)]


# For UGE
class JTImplementationSpecific(Structure):
    _fields_ = [("uge_jt_pe", drmaa2_string)]


class DRMAA2_JTEMPLATE(Structure):
    _fields_ = [("remotecommand", drmaa2_string),
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
                ("startTime", POINTER(TIME)),
                ("deadlineTime", POINTER(TIME)),
                ("stageInFiles", drmaa2_dict),
                ("stageOutFiles", drmaa2_dict),
                ("resourceLimits", drmaa2_dict),
                ("accountingId", drmaa2_string),
                ("implementationSpecific", c_void_p)]


class DRMAA2_RTEMPLATE(Structure):
    _fields_ = [("reservationName", drmaa2_string),
                ("startTime", POINTER(TIME)),
                ("endTime", POINTER(TIME)),
                ("duration", POINTER(TIME)),
                ("minSlots", c_longlong),
                ("maxSlots", c_longlong),
                ("jobCategory", drmaa2_string),
                ("usersACL", drmaa2_string_list),
                ("candidateMachines", drmaa2_string_list),
                ("minPhysMemory", c_longlong),
                ("machineOS", drmaa2_os),
                ("machineArch", drmaa2_cpu),
                ("implementationSpecific", c_void_p)]


class DRMAA2_NOTIFICATION(Structure):
    _fields_ = [("event", drmaa2_event),
                ("jobId", drmaa2_string),
                ("sessionName", drmaa2_string),
                ("jobState", drmaa2_jstate)]


class DRMAA2_QUEUEINFO(Structure):
    _fields_ = [("name", drmaa2_string),
                ("implementationSpecific", c_void_p)]


class DRMAA2_VERSION(Structure):
    _fields_ = [("major", drmaa2_string),
                ("minor", drmaa2_string)]


class DRMAA2_MACHINEINFO(Structure):
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


# UGE-specific
class DRMAA2_J(Structure):
    _fields_ = [("id", drmaa2_string),
                ("session_name", drmaa2_string)]


# UGE-specific
class DRMAA2_JARRAY(Structure):
    _fields_ = [("id", drmaa2_string),
                ("job_list", drmaa2_j_list),
                ("session_name", drmaa2_string)]


# UGE-specific
class DRMAA2_JSESSION(Structure):
    _fields_ = [("contact", drmaa2_string),
                ("name", drmaa2_string)]


# UGE-specific
class DRMAA2_MSESSION(Structure):
    _fields_ = [("name", drmaa2_string)]


# UGE-specific, and I can't find these definitions, so they will be opaque.
drmaa2_rsession = c_void_p
drmaa2_r = c_void_p


def load_drmaa_library():
    global DRMAA_LIB
    if DRMAA_LIB: return DRMAA_LIB
    SGE_ROOT = Path(os.environ["SGE_ROOT"])
    drmaa2_name = SGE_ROOT / "lib/lx-amd64" / "libdrmaa2.so"
    try:
        DRMAA_LIB = ctypes.cdll.LoadLibrary(str(drmaa2_name))
    except OSError as ose:
        raise Exception("Cannot open the DRMAA_LIB for DRMAA", ose)
    print("initializing DRMAA2")

    DRMAA_LIB.drmaa2_string_free.restype = None
    DRMAA_LIB.drmaa2_string_free.argtypes = [drmaa2_string]

    DRMAA_LIB.drmaa2_list_create.restype = drmaa2_list
    DRMAA_LIB.drmaa2_list_create.argtypes =\
            [drmaa2_listtype, DRMAA2_LIST_ENTRYFREE]
    DRMAA_LIB.drmaa2_list_free.restype = None
    DRMAA_LIB.drmaa2_list_free.argtypes = [drmaa2_list]
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
    DRMAA_LIB.uge_drmaa2_list_free_root.argtypes = [drmaa2_list]
    # Nonstandard
    DRMAA_LIB.uge_drmaa2_list_set.restype = drmaa2_error
    DRMAA_LIB.uge_drmaa2_list_set.argtypes = [drmaa2_list, c_long, c_void_p]

    DRMAA_LIB.drmaa2_dict_create.restype = drmaa2_dict
    DRMAA_LIB.drmaa2_dict_create.argtypes = [DRMAA2_DICT_ENTRYFREE]
    DRMAA_LIB.drmaa2_dict_free.restype = None
    DRMAA_LIB.drmaa2_dict_free.argtypes = [drmaa2_dict]
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
    DRMAA_LIB.drmaa2_jinfo_free.argtypes = [POINTER(DRMAA2_JINFO)]

    DRMAA_LIB.drmaa2_slotinfo_free.restype = None
    DRMAA_LIB.drmaa2_slotinfo_free.argtypes = [POINTER(DRMAA2_SLOTINFO)]

    DRMAA_LIB.drmaa2_rinfo_free.restype = None
    DRMAA_LIB.drmaa2_rinfo_free.argtypes = [POINTER(DRMAA2_RINFO)]

    DRMAA_LIB.drmaa2_jtemplate_create.restype = POINTER(DRMAA2_JTEMPLATE)
    DRMAA_LIB.drmaa2_jtemplate_create.argtypes = []
    DRMAA_LIB.drmaa2_jtemplate_free.restype = None
    DRMAA_LIB.drmaa2_jtemplate_free.argtypes = [POINTER(DRMAA2_JTEMPLATE)]

    DRMAA_LIB.drmaa2_rtemplate_create.restype = POINTER(DRMAA2_RTEMPLATE)
    DRMAA_LIB.drmaa2_rtemplate_create.argtypes = []
    DRMAA_LIB.drmaa2_rtemplate_free.restype = None
    DRMAA_LIB.drmaa2_rtemplate_free.argtypes = [POINTER(DRMAA2_RTEMPLATE)]

    DRMAA_LIB.drmaa2_notification_free.restype = None
    DRMAA_LIB.drmaa2_notification_free.argtypes = [POINTER(DRMAA2_NOTIFICATION)]

    DRMAA_LIB.drmaa2_queueinfo_free.restype = None
    DRMAA_LIB.drmaa2_queueinfo_free.argtypes = [POINTER(DRMAA2_QUEUEINFO)]

    DRMAA_LIB.drmaa2_version_free.restype = None
    DRMAA_LIB.drmaa2_version_free.argtypes = [POINTER(DRMAA2_VERSION)]

    DRMAA_LIB.drmaa2_machineinfo_free.restype = None
    DRMAA_LIB.drmaa2_machineinfo_free.argtypes = [POINTER(DRMAA2_MACHINEINFO)]

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
    DRMAA_LIB.drmaa2_jsession_free.argtypes = [POINTER(DRMAA2_JSESSION)]
    DRMAA_LIB.drmaa2_rsession_free.restype = None
    DRMAA_LIB.drmaa2_rsession_free.argtypes = [POINTER(drmaa2_rsession)]
    DRMAA_LIB.drmaa2_msession_free.restype = None
    DRMAA_LIB.drmaa2_msession_free.argtypes = [POINTER(DRMAA2_MSESSION)]
    DRMAA_LIB.drmaa2_j_free.restype = None
    DRMAA_LIB.drmaa2_j_free.argtypes = [POINTER(DRMAA2_J)]
    DRMAA_LIB.drmaa2_jarray_free.restype = None
    DRMAA_LIB.drmaa2_jarray_free.argtypes = [POINTER(DRMAA2_JARRAY)]
    # These are in the header drmaa2.h but not libdrmaa2.so.
    # DRMAA_LIB.drmaa2_r_free.restype = None
    # DRMAA_LIB.drmaa2_r_free.argtypes = [DRMAA2_R]

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
    DRMAA_LIB.drmaa2_jarray_get_id.argtypes = [POINTER(DRMAA2_JARRAY)]
    DRMAA_LIB.drmaa2_jarray_get_jobs.restype = drmaa2_j_list
    DRMAA_LIB.drmaa2_jarray_get_jobs.argtypes = [POINTER(DRMAA2_JARRAY)]
    DRMAA_LIB.drmaa2_jarray_get_session_name.restype = drmaa2_string
    DRMAA_LIB.drmaa2_jarray_get_session_name.argtypes = [POINTER(DRMAA2_JARRAY)]
    DRMAA_LIB.drmaa2_jarray_get_jtemplate.restype = POINTER(DRMAA2_JTEMPLATE)
    DRMAA_LIB.drmaa2_jarray_get_jtemplate.argtypes = [POINTER(DRMAA2_JARRAY)]
    DRMAA_LIB.drmaa2_jarray_suspend.restype = drmaa2_error
    DRMAA_LIB.drmaa2_jarray_suspend.argtypes = [POINTER(DRMAA2_JARRAY)]
    DRMAA_LIB.drmaa2_jarray_resume.restype = drmaa2_error
    DRMAA_LIB.drmaa2_jarray_resume.argtypes = [POINTER(DRMAA2_JARRAY)]
    DRMAA_LIB.drmaa2_jarray_hold.restype = drmaa2_error
    DRMAA_LIB.drmaa2_jarray_hold.argtypes = [POINTER(DRMAA2_JARRAY)]
    DRMAA_LIB.drmaa2_jarray_release.restype = drmaa2_error
    DRMAA_LIB.drmaa2_jarray_release.argtypes = [POINTER(DRMAA2_JARRAY)]
    DRMAA_LIB.drmaa2_jarray_terminate.restype = drmaa2_error
    DRMAA_LIB.drmaa2_jarray_terminate.argtypes = [POINTER(DRMAA2_JARRAY)]

    DRMAA_LIB.drmaa2_jsession_get_contact.restype = drmaa2_string
    DRMAA_LIB.drmaa2_jsession_get_contact.argtypes = [
        POINTER(DRMAA2_JSESSION)]
    DRMAA_LIB.drmaa2_jsession_get_session_name.restype = drmaa2_string
    DRMAA_LIB.drmaa2_jsession_get_session_name.argtypes = [
        POINTER(DRMAA2_JSESSION)]
    DRMAA_LIB.drmaa2_jsession_get_job_categories.restype = drmaa2_string_list
    DRMAA_LIB.drmaa2_jsession_get_job_categories.argtypes = [
        POINTER(DRMAA2_JSESSION)]
    DRMAA_LIB.drmaa2_jsession_get_jobs.restype = drmaa2_j_list
    DRMAA_LIB.drmaa2_jsession_get_jobs.argtypes = [POINTER(DRMAA2_JSESSION),
                                                   POINTER(DRMAA2_JINFO)]
    DRMAA_LIB.drmaa2_jsession_get_job_array.restype = POINTER(DRMAA2_JARRAY)
    DRMAA_LIB.drmaa2_jsession_get_job_array.argtypes = [
        POINTER(DRMAA2_JSESSION), drmaa2_string]
    DRMAA_LIB.drmaa2_jsession_run_job.restype = POINTER(DRMAA2_J)
    DRMAA_LIB.drmaa2_jsession_run_job.argtypes = [POINTER(DRMAA2_JSESSION),
                                                  POINTER(DRMAA2_JTEMPLATE)]
    DRMAA_LIB.drmaa2_jsession_run_bulk_jobs.restype = POINTER(DRMAA2_JARRAY)
    DRMAA_LIB.drmaa2_jsession_run_bulk_jobs.argtypes = [
        POINTER(DRMAA2_JSESSION), POINTER(DRMAA2_JTEMPLATE),
        c_longlong, c_longlong, c_longlong, c_longlong]
    DRMAA_LIB.drmaa2_jsession_wait_any_started.restype = POINTER(DRMAA2_J)
    DRMAA_LIB.drmaa2_jsession_wait_any_started.argtypes = [
        POINTER(DRMAA2_JSESSION), drmaa2_j_list, POINTER(TIME)]
    DRMAA_LIB.drmaa2_jsession_wait_any_terminated.restype = POINTER(DRMAA2_J)
    DRMAA_LIB.drmaa2_jsession_wait_any_terminated.argtypes = [
        POINTER(DRMAA2_JSESSION), drmaa2_j_list, POINTER(TIME)]
    DRMAA_LIB.drmaa2_j_suspend.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_suspend.argtypes = [POINTER(DRMAA2_J)]
    DRMAA_LIB.drmaa2_j_resume.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_resume.argtypes = [POINTER(DRMAA2_J)]
    DRMAA_LIB.drmaa2_j_release.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_release.argtypes = [POINTER(DRMAA2_J)]
    DRMAA_LIB.drmaa2_j_terminate.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_terminate.argtypes = [POINTER(DRMAA2_J)]
    DRMAA_LIB.drmaa2_j_reap.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_reap.argtypes = [POINTER(DRMAA2_J)]
    DRMAA_LIB.drmaa2_j_get_id.restype = drmaa2_string
    DRMAA_LIB.drmaa2_j_get_id.argtypes = [POINTER(DRMAA2_J)]
    DRMAA_LIB.drmaa2_j_get_jtemplate.restype = POINTER(DRMAA2_JTEMPLATE)
    DRMAA_LIB.drmaa2_j_get_jtemplate.argtypes = [POINTER(DRMAA2_J)]
    DRMAA_LIB.drmaa2_j_get_state.restype = drmaa2_jstate
    DRMAA_LIB.drmaa2_j_get_state.argtypes = [POINTER(DRMAA2_J)]
    DRMAA_LIB.drmaa2_j_get_info.restype = POINTER(DRMAA2_JINFO)
    DRMAA_LIB.drmaa2_j_get_info.argtypes = [POINTER(DRMAA2_J)]
    DRMAA_LIB.drmaa2_j_wait_started.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_wait_started.argtypes = [POINTER(DRMAA2_J), POINTER(TIME)]
    DRMAA_LIB.drmaa2_j_wait_terminated.restype = drmaa2_error
    DRMAA_LIB.drmaa2_j_wait_terminated.argtypes = [POINTER(DRMAA2_J)]

    DRMAA_LIB.drmaa2_msession_get_all_reservations.restype = drmaa2_r_list
    DRMAA_LIB.drmaa2_msession_get_all_reservations.argtypes = [
        POINTER(DRMAA2_MSESSION)]
    DRMAA_LIB.drmaa2_msession_get_all_jobs.restype = drmaa2_j_list
    DRMAA_LIB.drmaa2_msession_get_all_jobs.argtypes = [POINTER(DRMAA2_MSESSION),
                                                       POINTER(DRMAA2_JINFO)]
    DRMAA_LIB.drmaa2_msession_get_all_queues.restype = drmaa2_queueinfo_list
    DRMAA_LIB.drmaa2_msession_get_all_queues.argtypes = [
        POINTER(DRMAA2_MSESSION), drmaa2_string_list]
    DRMAA_LIB.drmaa2_msession_get_all_machines.restype = drmaa2_machineinfo_list
    DRMAA_LIB.drmaa2_msession_get_all_machines.argtypes = [
        POINTER(DRMAA2_MSESSION), drmaa2_string_list]

    DRMAA_LIB.drmaa2_get_drms_name.restype = drmaa2_string
    DRMAA_LIB.drmaa2_get_drms_name.argtypes = []
    DRMAA_LIB.drmaa2_get_drms_version.restype = POINTER(DRMAA2_VERSION)
    DRMAA_LIB.drmaa2_get_drms_version.argtypes = []
    DRMAA_LIB.drmaa2_supports.restype = drmaa2_bool
    DRMAA_LIB.drmaa2_supports.argtypes = [drmaa2_capability]
    DRMAA_LIB.drmaa2_create_jsession.restype = POINTER(DRMAA2_JSESSION)
    DRMAA_LIB.drmaa2_create_jsession.argtypes = [c_char_p, c_char_p]
    DRMAA_LIB.drmaa2_create_rsession.restype = drmaa2_rsession
    DRMAA_LIB.drmaa2_create_rsession.argtypes = [c_char_p, c_char_p]
    DRMAA_LIB.drmaa2_open_jsession.restype = POINTER(DRMAA2_JSESSION)
    DRMAA_LIB.drmaa2_open_jsession.argtypes = [c_char_p]
    DRMAA_LIB.drmaa2_open_rsession.restype = drmaa2_rsession
    DRMAA_LIB.drmaa2_open_rsession.argtypes = [c_char_p]
    DRMAA_LIB.drmaa2_open_msession.restype = POINTER(DRMAA2_MSESSION)
    DRMAA_LIB.drmaa2_open_msession.argtypes = [c_char_p]
    DRMAA_LIB.drmaa2_close_jsession.restype = drmaa2_error
    DRMAA_LIB.drmaa2_close_jsession.argtypes = [POINTER(DRMAA2_JSESSION)]
    DRMAA_LIB.drmaa2_close_rsession.restype = drmaa2_error
    DRMAA_LIB.drmaa2_close_rsession.argtypes = [drmaa2_rsession]
    DRMAA_LIB.drmaa2_close_msession.restype = drmaa2_error
    DRMAA_LIB.drmaa2_close_msession.argtypes = [POINTER(DRMAA2_MSESSION)]
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

