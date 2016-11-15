"""
This creates classes around the Session interface of
the DRMAA2 library using the interface module to
provide access to the native library.
"""
import collections
from ctypes import byref
from uuid import uuid4
from .interface import *
from .errors import *
from .wrapping import *


LOGGER = logging.getLogger("drmaa2.session")
DRMAA_LIB = load_drmaa_library()


def job_template_implementation_specific():
    string_list = DRMAA_LIB.drmaa2_jtemplate_impl_spec()
    return convert_and_free_string_list(string_list)


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
    implementationSpecific = DRMAA2String("implementationSpecific")

    def implementation_specific(self):
        return implementation_specific(DRMAA_LIB.drmaa2_jtemplate_impl_spec)

    def get_impl_spec(self, name):
        d_string = DRMAA_LIB.drmaa2_get_instance_value(
            cast(self._wrapped, c_void_p),
            name.encode())
        # This can sometimes cast a spurious error that the value isn't
        # specified, even though the value is just currently unset.
        if last_errno() < 1:
            return return_str(d_string)
        else:
            raise DRMAA2Exception(last_error())

    def set_impl_spec(self, name, value):
        CheckError(DRMAA_LIB.drmaa2_set_instance_value(
            self._wrapped, name.encode(), value.encode())
        )

    def __repr__(self):
        return "JobTemplate" + self.__str__()

    def __str__(self):
        report = list()
        attributes = [field[0] for field in self._wrapped.contents._fields_]
        for attr_name in sorted(attributes):
            try:
                v = getattr(self, attr_name)
                if v:
                    report.append("{}={}".format(attr_name, str(v)))
            except AttributeError:
                pass  # eh, OK. the names don't line up.
        return "({})".format(", ".join(report))


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

@conversion_strategy(ListType.joblist)
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


class Notification:
    def __init__(self, notification_struct):
        self._wrapped = notification_struct

    event = DRMAA2Enum("event", Event)
    jobId = DRMAA2String("jobId")
    sessionName = DRMAA2String("sessionName")
    jobState = DRMAA2Enum("jobState", JState)


class JobSession:
    def __init__(self, name=None, contact=None, keep=False):
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
        self._open = True
        self.name = name
        self.keep = keep

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self.__del__()
        if not self.keep:
            self.destroy()

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
        obj._open = True
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
        if self._open:
            CheckError(DRMAA_LIB.drmaa2_close_jsession(self._session))
            self._open = False

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

    def __del__(self):
        """This frees allocated free store to hold the session.
        Call this after closing the session."""
        LOGGER.debug("free JobSession")
        if self._session:
            DRMAA_LIB.drmaa2_jsession_free(pointer(self._session))  # void
            self._session = None

    @property
    def contact(self):
        contact_str = DRMAA_LIB.drmaa2_jsession_get_contact(self._session)
        if contact_str:
            return contact_str.decode()
        else:
            return None

    def run(self, job_template):
        LOGGER.debug("enter run of {}".format(job_template))
        job = DRMAA_LIB.drmaa2_jsession_run_job(
            self._session, job_template._wrapped)
        if not job:
            LOGGER.debug("Error submitting job.")
            raise RuntimeError(last_error())
        job_obj = JobStrategy.from_ptr(job)
        LOGGER.debug("run returning {}".format(job_obj))
        DRMAA_LIB.drmaa2_j_free(job)
        return job_obj

    def wait_any_terminated(self, job_list, how_long):
        """
        What is the next job that completes on the job list.
        All jobs in the job list must be part of this session.

        :param job_list: Either a list of Job objects or a DRMAA2List.
        :param how_long: Length as seconds, or the enum Times.infinite,
                         Times.now, or the string "infinite" or "now" or "zero".
        :return: a Job object or None
        """
        if isinstance(how_long, int):
            try:
                how_long = Times(how_long)
            except ValueError:
                if __name__ == '__main__':
                    pass  # Well, the integer may be correct
        elif isinstance(how_long, str):
            how_long = Times[how_long]
        else:
            how_long = how_long.value
        if isinstance(job_list, DRMAA2List):
            jobs_ptr = job_list.list_ptr
        else:
            jobs_ptr = DRMAA2List(job_list, ListType.joblist).list_ptr
        job_ptr = DRMAA_LIB.drmaa2_jsession_wait_any_terminated(
            self._session, jobs_ptr, how_long)
        if job_ptr:
            job = JobStrategy.from_ptr(job_ptr)
            DRMAA_LIB.drmaa2_j_free(job)
            return job
        else:
            return None

