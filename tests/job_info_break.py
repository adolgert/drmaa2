import ctypes
import drmaa2


def job_info_break():
    lib = drmaa2.interface.load_drmaa_library()
    ji = lib.drmaa2_jinfo_create()
    ji.contents.jobId.value = b"1234"
    lib.drmaa2_jinfo_free(ctypes.byref(ji))


def job_info_fix():
    lib = drmaa2.interface.load_drmaa_library()
    ji = lib.drmaa2_jinfo_create()
    ji.contents.jobId.value = b"1234"
    ji.contents.jobId = drmaa2.interface.drmaa2_string(0)
    lib.drmaa2_jinfo_free(ctypes.byref(ji))


if __name__ == "__main__":
    job_info_fix()
    print("and now break")
    job_info_break()
