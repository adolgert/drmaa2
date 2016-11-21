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


class JobArray(object):
    """
    A set of jobs that are treated together.

    Concerns for wrapping: This object has methods, so it shouldn't
    be a namedtuple. It is always returned by DRMAA2, never created
    by the client, so maybe it should just be a Python object
    that gets copied into a native object when necessary.
    It's something we would like to serialize, possibly, because
    it has the list of job ids. What it contains, however, is
    implementation-specific, so UGE saves the id, job list, and
    session name. That means the contents of the job list
    have to be determined from a lookup to see what UGE uses
    if we want to make one of our own.
    """
    def __init__(self, existing):
        self._wrapped = existing

    @property
    def id(self):
        return return_str(DRMAA_LIB.drmaa2_jarray_get_id(self._wrapped))

    @property
    def jobs(self):
        jobs_ptr = DRMAA_LIB.drmaa2_jarray_get_jobs(self._wrapped)
        if jobs_ptr:
            return DRMAA2List.from_existing(jobs_ptr, ListType.joblist)
        else:
            check_errno()
            return None

    @property
    def session_name(self):
        return return_str(DRMAA_LIB.drmaa2_jarray_get_session_name(
            self._wrapped))

    @property
    def job_template(self):
        jt_ptr = DRMAA_LIB.drmaa2_jarray_get_jtemplate(self._wrapped)
        if jt_ptr:
            return JobTemplate(jt_ptr)
        else:
            raise RuntimeError(last_error())

    def suspend(self):
        CheckError(DRMAA_LIB.drmaa2_jarray_suspend(self._wrapped))

    def resume(self):
        CheckError(DRMAA_LIB.drmaa2_jarray_resume(self._wrapped))

    def hold(self):
        CheckError(DRMAA_LIB.drmaa2_jarray_hold(self._wrapped))

    def release(self):
        CheckError(DRMAA_LIB.drmaa2_jarray_release(self._wrapped))

    def terminate(self):
        CheckError(DRMAA_LIB.drmaa2_jarray_terminate(self._wrapped))

    def __del__(self):
        if self._wrapped:
            DRMAA_LIB.drmaa2_jarray_free(byref(self._wrapped))
            self._wrapped = None


@Extensible(DRMAA_LIB.drmaa2_jinfo_impl_spec)
@Wraps(DRMAA2_JINFO)
class JobInfo:
    def __init__(self, existing=None):
        """
        If an existing JobInfo struct is an argument, then this
        object becomes responsible for deleting it.

        :param POINTER(DRMAA2_JINFO) existing: A native pointer.
        """
        if existing:
            self._wrapped = existing
        else:
            self._wrapped = DRMAA_LIB.drmaa2_jinfo_create()

    jobId = DRMAA2String()
    exitStatus = DRMAA2String()
    terminatingSignal = DRMAA2String()
    annotation = DRMAA2String()
    jobState = DRMAA2String()
    jobSubState = DRMAA2String()
    allocatedMachines = DRMAA2StringList(ListType.stringlist)
    submissionMachine = DRMAA2String()
    jobOwner = DRMAA2String()
    slots = DRMAA2LongLong()
    queueName = DRMAA2String()
    wallclockTime = DRMAA2Time()
    cpuTime = DRMAA2LongLong()
    submissionTime = DRMAA2Time()
    dispatchTime = DRMAA2Time()
    finishTime = DRMAA2Time()

    def __del__(self):
        if self._wrapped:
            DRMAA_LIB.drmaa2_jinfo_free(byref(self._wrapped))
            self._wrapped = None


def _jinfo_crash():
    _wrapped = DRMAA_LIB.drmaa2_jinfo_create()
    DRMAA_LIB.drmaa2_jinfo_free(_wrapped)


def job_template_implementation_specific():
    string_list = DRMAA_LIB.drmaa2_jtemplate_impl_spec()
    return convert_and_free_string_list(string_list)


@Extensible(DRMAA_LIB.drmaa2_jtemplate_impl_spec)
@Wraps(DRMAA2_JTEMPLATE)
class JobTemplate:
    """A JobTemplate is how you say what executable to run
    with what parameters.

    This class is a layer on top of a ctypes wrapper for the
    drmaa2_jtemplate class.
    """
    def __init__(self, existing=None):
        if existing:
            self._wrapped = existing
        else:
            # _wrapped is a pointer to a DRMAA_JTEMPLATE.
            self._wrapped = DRMAA_LIB.drmaa2_jtemplate_create()

    # These are properties that translate between pythonic
    # entities and the ctypes storage.
    remoteCommand = DRMAA2String()
    """Path to executable or shell script"""
    args = DRMAA2StringList(ListType.stringlist)
    """Arguments to the remoteCommand as a list of strings."""
    submitAsHold = DRMAA2Bool()
    """The job should start in a held state."""
    rerunnable = DRMAA2Bool()
    """If a job returns exit code 100, put it into a held state."""
    jobEnvironment = DRMAA2Dict()
    """A dictionary of environment variables, all strings."""
    workingDirectory = DRMAA2String()
    """Working directory for the process."""
    jobCategory = DRMAA2String()
    """A category is a default set of job attributes, defined on installation."""
    email = DRMAA2StringList(ListType.stringlist)
    """List of email addresses."""
    emailOnStarted = DRMAA2Bool()
    """Whether to email the addresses when a job starts. (bool"""
    emailOnTerminated = DRMAA2Bool()
    """Whether to email the address when a job finishes. (bool)"""
    jobName = DRMAA2String()
    """A string name for the job."""
    inputPath = DRMAA2String()
    """A string path for an input file as stdin."""
    outputPath = DRMAA2String()
    """A string path for an output file pattern."""
    errorPath = DRMAA2String()
    """A string path for an error file pattern."""
    joinFiles = DRMAA2Bool()
    """Whether to combine output and error into one file."""
    reservationId = DRMAA2String()
    """The string name of a reservation under which to run this job."""
    queueName = DRMAA2String()
    """The string name of a queue for this job."""
    minSlots = DRMAA2LongLong()
    """An integer number of slots for Array jobs which
    have uge_jt_pe=multi_slot."""
    maxSlots = DRMAA2LongLong()
    """An integer number of slots for Array jobs which
    have uge_jt_pe=multi_slot."""
    priority = DRMAA2LongLong()
    """A job priority. Users can move it down only."""
    candidateMachines = DRMAA2StringList(ListType.stringlist)
    """Machine names where this template could run."""
    minPhysMemory = DRMAA2LongLong()
    """A minimum amount of physical memory as an int."""
    machineOS = DRMAA2Enum(OS)
    """Desired machine operating system, from the OS Enum."""
    machineArch = DRMAA2Enum(CPU)
    """Desired machine architecture, from the CPU enum."""
    startTime = DRMAA2Time()
    """A start time for the job, in seconds."""
    deadlineTime = DRMAA2Time()
    """A deadline time for start, in seconds."""
    stageInFiles = DRMAA2Dict()
    """A list of files to transfer before the job, if supported."""
    stageOutFiles = DRMAA2Dict()
    """A list of files to transfer after the job, if supported."""
    resourceLimits = DRMAA2Dict()
    """A list of desired resources, as a dict of strings where
    the keys are from the ResourceLimits Enum."""
    accountingId = DRMAA2Dict()
    """A dictionary of accounting information."""

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


def describe(self, name):
    """Get the text description of an implementation-specific
    attribute.

    :param name str: From the list of implementation-specific names.
    :return str: A description.
    """
    d_string = DRMAA_LIB.drmaa2_describe_attribute(
        cast(self.parent._wrapped, c_void_p), name.encode())
    return return_str(d_string)


class JobSession:
    """The JobSession is the central class for running jobs.
    This Python class wraps a ctypes.Structure called
    DRMAA2_JSESSION."""
    def __init__(self, name=None, contact=None, keep=False):
        """
        Create a session, or open it if it exists already.
        The IDL description says this should have a contact name,
        but it isn't supported. UGE always makes the contact your
        user name.

        :param str name: Choose a name for this job session. If you don't,
                         then it will use "default" as a name.
        :param str contact: Maybe leave this None.
        :param bool keep: This says whether to destroy this
                          session when it is reaped. Sessions normally
                          live forever until you destroy them.
        """
        name = name or "default"
        LOGGER.debug("Creating JobSession {}".format(name))
        contact_str = contact.encode() if contact else c_char_p()
        self._session = DRMAA_LIB.drmaa2_create_jsession(
                name.encode(), contact_str)
        if not self._session:
            if Error.internal == last_errno():
                LOGGER.debug("Session may exist. Opening it.")
                self._session = DRMAA_LIB.drmaa2_open_jsession(
                        name.encode(), contact_str)
                LOGGER.debug("Session opened {}".format(bool(self._session)))
                # XXX The error is still set after open_jsession succeeds.
                # XXX Succeeding should clear errno.
                if not self._session:
                    raise RuntimeError(last_error())
            else:
                raise RuntimeError(last_error())
        self._open = True
        self._name = name
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

    @property
    def job_categories(self):
        cat_list = DRMAA_LIB.drmaa2_jsession_get_job_categories(
            self._session)
        if cat_list:
            return DRMAA2List.from_existing(cat_list, ListType.stringlist)
        else:
            check_errno()
            return None

    @property
    def jobs(self):
        return self.jobs_matching()

    def jobs_matching(self, job_info=None):
        jobs_ptr = DRMAA_LIB.drmaa2_jsession_get_jobs(
            self._session, job_info._wrapped)
        if jobs_ptr:
            return DRMAA2List.from_existing(jobs_ptr, ListType.joblist)
        else:
            check_errno()
            return None

    def job_array(self, job_array_id):
        """
        Get a job array that is in this session.

        :param str job_array_id: The name of the job array.
        :return:
        """
        return None

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

    @property
    def name(self):
        if self._name:
            return self._name
        else:
            name_str = DRMAA_LIB.drmaa2_jsession_get_session_name(
                                self._session)
            if name_str:
                return name_str.decode()
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

    def as_terminated(self, job_list, how_long=Times.infinite):
        """
        A generator that yields each job as it completes.
        It makes a copy of the incoming list because, as it works,
        it removes entries from the list.

        :param job_list: Either a list of Job objects or a DRMAA2List.
        :param how_long: Length as seconds, or the enum Times.infinite,
                         or the string "infinite".
        :return: a Job object or raises StopIteration.
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
            jobs = DRMAA2List(list(job_list), ListType.joblist)
        else:
            jobs = DRMAA2List(job_list, ListType.joblist)

        job_ptr = True
        while job_ptr and len(jobs) > 0:
            LOGGER.debug("as_terminated waiting for {} jobs {}".format(
                len(jobs), how_long
            ))
            job_ptr = DRMAA_LIB.drmaa2_jsession_wait_any_terminated(
                self._session, jobs.list_ptr, drmaa2_time(how_long))
            if job_ptr:
                job = JobStrategy.from_ptr(job_ptr)
                # The returned job_ptr is NOT a copy, so don't free it.
                yield job
                removed = jobs.remove_ptr(job_ptr)
                assert removed
            else:
                if last_errno() == Error.timeout:
                    # Timeout isn't an error.
                    return None
                else:
                    check_errno()
        else:
            jobs.__del__()
        raise StopIteration()
