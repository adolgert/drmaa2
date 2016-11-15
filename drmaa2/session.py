"""
This creates classes around the Session interface of
the DRMAA2 library using the interface module to
provide access to the native library.

.. image:: DRMAA2Job.*
   :alt: Three entry points are JobSession, JobInfo, and JobTemplate. They create Jobs or JobArrays. They interact with reservations only through the reservation ID.

"""
import collections
from ctypes import cast
from ctypes import byref
from uuid import uuid4
from .interface import *
from .errors import *
from .wrapping import *


LOGGER = logging.getLogger("drmaa2.session")
DRMAA_LIB = load_drmaa_library()


Job = collections.namedtuple("Job", "id sessionName")
Job.__doc__ = """This is the class that represents jobs.
It's enough so far."""
Job.id.__doc__ = "Python string of SGE Job ID."
Job.sessionName.__doc__ = "Python string of Job Session name."


def job_template_implementation_specific():
    string_list = DRMAA_LIB.drmaa2_jtemplate_impl_spec()
    return convert_and_free_string_list(string_list)


class JobTemplate:
    """A JobTemplate is how you say what executable to run
    with what parameters.

    This class is a layer on top of a ctypes wrapper for the
    drmaa2_jtemplate class.
    """
    def __init__(self):
        # _wrapped is a pointer to a DRMAA_JTEMPLATE.
        self._wrapped = DRMAA_LIB.drmaa2_jtemplate_create()

    # These are properties that translate between pythonic
    # entities and the ctypes storage.
    remoteCommand = DRMAA2String("remoteCommand")
    """Path to executable or shell script"""
    args = DRMAA2StringList("args", ListType.stringlist)
    """Arguments to the remoteCommand as a list of strings."""
    submitAsHold = DRMAA2Bool("submitAsHold")
    """The job should start in a held state."""
    rerunnable = DRMAA2Bool("rerunnable")
    """If a job returns exit code 100, put it into a held state."""
    jobEnvironment = DRMAA2Dict("jobEnvironment")
    """A dictionary of environment variables, all strings."""
    workingDirectory = DRMAA2String("workingDirectory")
    """Working directory for the process."""
    jobCategory = DRMAA2String("jobCategory")
    """A category is a default set of job attributes, defined on installation."""
    email = DRMAA2StringList("email", ListType.stringlist)
    """List of email addresses."""
    emailOnStarted = DRMAA2Bool("emailOnStarted")
    """Whether to email the addresses when a job starts. (bool"""
    emailOnTerminated = DRMAA2Bool("emailOnTerminated")
    """Whether to email the address when a job finishes. (bool)"""
    jobName = DRMAA2String("jobName")
    """A string name for the job."""
    inputPath = DRMAA2String("inputPath")
    """A string path for an input file as stdin."""
    outputPath = DRMAA2String("outputPath")
    """A string path for an output file pattern."""
    errorPath = DRMAA2String("errorPath")
    """A string path for an error file pattern."""
    joinFiles = DRMAA2Bool("joinFiles")
    """Whether to combine output and error into one file."""
    reservationId = DRMAA2String("reservationId")
    """The string name of a reservation under which to run this job."""
    queueName = DRMAA2String("queueName")
    """The string name of a queue for this job."""
    minSlots = DRMAA2LongLong("minSlots")
    """An integer number of slots for Array jobs which
    have uge_jt_pe=multi_slot."""
    maxSlots = DRMAA2LongLong("maxSlots")
    """An integer number of slots for Array jobs which
    have uge_jt_pe=multi_slot."""
    priority = DRMAA2LongLong("priority")
    """A job priority. Users can move it down only."""
    candidateMachines = DRMAA2StringList("candidateMachines",
                                         ListType.stringlist)
    """Machine names where this template could run."""
    minPhysMemory = DRMAA2LongLong("minPhysMemory")
    """A minimum amount of physical memory as an int."""
    machineOS = DRMAA2Enum("machineOS", OS)
    """Desired machine operating system, from the OS Enum."""
    machineArch = DRMAA2Enum("machineArch", CPU)
    """Desired machine architecture, from the CPU enum."""
    startTime = DRMAA2Time("startTime")
    """A start time for the job, in seconds."""
    deadlineTime = DRMAA2Time("deadlineTime")
    """A deadline time for start, in seconds."""
    stageInFiles = DRMAA2Dict("stageInFiles")
    """A list of files to transfer before the job, if supported."""
    stageOutFiles = DRMAA2Dict("stageOutFiles")
    """A list of files to transfer after the job, if supported."""
    resourceLimits = DRMAA2Dict("resourceLimits")
    """A list of desired resources, as a dict of strings where
    the keys are from the ResourceLimits Enum."""
    accountingId = DRMAA2Dict("accountingId")
    """A dictionary of accounting information."""

    def implementation_specific(self):
        """Each implementation of DRMAA (UGE, SGE, etc) can add
        entries to this struct. This is how you discover those
        entities."""
        return implementation_specific(DRMAA_LIB.drmaa2_jtemplate_impl_spec)

    def get_impl_spec(self, name):
        """Each entity has a string name and a string value (I think).
        If the value isn't set, then you could get an exception,
        at least in UGE, so try setting it before you get it.

        :param name str: string name of the entity
        :returns str: The value.
        """
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
        """This sets implementation-specific entities.

        :param name str: string name of the entity
        :param value str: string value of the entity.
        """
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
    """A function outside of the class to get implementation-specific
    strings and values.

    :param parent: A class with a member _wrapped that is a pointer to
                   the ctypes class.
    :param name str: The name from the list of implementation-specific
                     names.
    :param checker: Each struct that has implementation-specific
                    members has its own function to check for them,
                    such as drmaa2_jtemplate_impl_spec.
    """
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
    """A function outside of the class to get implementation-specific
    strings and values.

    :param parent: A class with a member _wrapped that is a pointer to
                   the ctypes class.
    :param name str: The name from the list of implementation-specific
                     names.
    :param checker: Each struct that has implementation-specific
                    members has its own function to check for them,
                    such as drmaa2_jtemplate_impl_spec.
    """
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
    """Get the text description of an implementation-specific
    attribute.

    :param name str: From the list of implementation-specific names.
    :return str: A description.
    """
    d_string = DRMAA_LIB.drmaa2_describe_attribute(
        cast(self.parent._wrapped, c_void_p), name.encode())
    return return_str(d_string)


# The conversion strategy is defined in wrapping module.
# It says to register this class as a set of helper functions
# to store and retrieve Jobs from a drmaa2_list of jobs.
@conversion_strategy(ListType.joblist)
class JobStrategy:
    @staticmethod
    def from_void(void_ptr):
        """Given a ctypes.c_void_p, return a Job."""
        return JobStrategy.from_ptr(cast(void_ptr, POINTER(DRMAA2_J)))

    @staticmethod
    def from_ptr(void_ptr):
        """Given a DRMAA2Job (ctypes.Structure to wrap a job),
        return a Job."""
        j = cast(void_ptr, POINTER(DRMAA2_J))
        if j:
            c = j.contents
            return Job(c.id.value.decode(), c.sessionName.value.decode())
        else:
            return None

    @staticmethod
    def to_void(job):
        """Given a Pythonic Job, return a pointer to a ctypes.Structure."""
        j = DRMAA2_J()
        j.id = job.id.encode()
        j.sessionName = job.sessionName.encode()
        return byref(j)

    @staticmethod
    def compare_pointers(a, b):
        """For searching a list, is this value equal to the one
        we are searching for? Arguments are ctypes pointers."""
        return JobStrategy.from_void(a) == JobStrategy.from_void(b)
        # return libc.memcmp(a, b, ctypes.sizeof(DRMAA2_J))


class Notification:
    """Represents a notification, which is passed back to a callback.
    This wrapps a DRMAA2Notification."""
    def __init__(self, notification_struct):
        self._wrapped = notification_struct

    event = DRMAA2Enum("event", Event)
    jobId = DRMAA2String("jobId")
    sessionName = DRMAA2String("sessionName")
    jobState = DRMAA2Enum("jobState", JState)


class JobSession:
    """The JobSession is the central class for running jobs.
    This Python class wraps a ctypes.Structure called
    DRMAA2_JSESSION."""
    def __init__(self, name=None, contact=None, keep=False):
        """The IDL description says this should have a contact name,
        but it isn't supported. UGE always makes the contact your
        user name.

        :param name str: Choose a name for this job session. If you don't,
                         then it will use a UUID.
        :param contact str: Maybe leave this None.
        :param keep bool: This says whether to destroy this
                          session when it is reaped. Sessions normally
                          live forever until you destroy them.
        """
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
        """Interface to make this a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure this is destroyed at the end and memory is freed."""
        self.close()
        self.__del__()
        if not self.keep:
            self.destroy()

    @classmethod
    def from_existing(cls, name):
        """Creates a JobSession from a name. This goes to the scheduler,
        finds the session with that name, and creates an interface
        to it.
        If user tangkend made JobSession crunch, then
        the job would be listed here as tangkend@crunch.

        :param name str: The string name from the names method.
        :return: JobSession instance.
        """
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
        """Ask the scheduler what job sessions exist.
        :return list(str): returns a list of names."""
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
        """Destroying a session removes it from the scheduler's memory.
        I wouldn't do this before it's closed."""
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
        """Actually run a job. Returns a Python Job instance.

        :param job_template JobTemplate: Fill out a template and this makes
                                         it happen.
        :return Job: The Job, meaning its job_id and session name.
        """
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
            self._session, jobs_ptr, drmaa2_time(how_long))
        if job_ptr:
            job = JobStrategy.from_ptr(job_ptr)
            # The returned job_ptr is NOT a copy, so don't free it.
            return job
        else:
            return None

