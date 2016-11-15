#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <drmaa2.h>


int job_with_hold() {
  drmaa2_jsession js = NULL;
  drmaa2_string error;
  drmaa2_jtemplate jt;
  drmaa2_j a, b;
  char* remote_command;
  drmaa2_string_list args;
  char* native_specification;
  int create_cnt = 2;
  int err;

  char name[]="adolgert1";
  printf("Making job session\n");
  while (NULL == js && create_cnt>0) {
      js = drmaa2_create_jsession(name, NULL);
      if (NULL == js) {
        err = drmaa2_lasterror();
        printf("error %d\n", drmaa2_lasterror());
        error = (drmaa2_string) drmaa2_lasterror_text();
        printf("Could not create session. %s\n", error);
        drmaa2_string_free(&error);
        if (6 == err) {
          drmaa2_destroy_jsession(name);
          printf("destroying session. will try again.");
        }
      }
      --create_cnt;
  }

  printf("Making job template\n");
  jt = drmaa2_jtemplate_create();
  if (NULL == jt) {
    printf("Can't make a template\n");
    return 3;
  }

  remote_command = strdup("/bin/sleep");
  jt->remoteCommand = remote_command;
  printf("Making list of arguments\n");
  args = drmaa2_list_create(DRMAA2_STRINGLIST, NULL);
  drmaa2_list_add(args, "60");
  jt->args = args;
  jtImplementationSpecific jtis = (jtImplementationSpecific) malloc(
        sizeof(jtImplementationSpecific_s));
  jtis->uge_jt_pe = strdup("multi_slot"); // strdup("-P proj_forecasting");
  if (jt->implementationSpecific == NULL) {
     printf("implementationSpecific starts out NULL\n");
  }
  jt->implementationSpecific = jtis;

  printf("Running a\n");
  a = drmaa2_jsession_run_job(js, jt);
      if (NULL == a) {
        err = drmaa2_lasterror();
        printf("error %d\n", drmaa2_lasterror());
        error = (drmaa2_string) drmaa2_lasterror_text();
        printf("Could not run job. %s\n", error);
        drmaa2_string_free(&error);
        return 3;
      }
  printf("Submitted %s\n", a->id);
  printf("Running b\n");
  b = drmaa2_jsession_run_job(js, jt);
      if (NULL == b) {
        err = drmaa2_lasterror();
        printf("error %d\n", drmaa2_lasterror());
        error = (drmaa2_string) drmaa2_lasterror_text();
        printf("Could not create session. %s\n", error);
        drmaa2_string_free(&error);
      }
  printf("Submitted %s\n", b->id);

  drmaa2_list jobs = drmaa2_list_create(DRMAA2_JOBLIST, NULL);
  drmaa2_list_add(jobs, a);
  drmaa2_list_add(jobs, b);
  int job_cnt = drmaa2_list_size(jobs);
  while (job_cnt > 0) {
    drmaa2_j res2 = drmaa2_jsession_wait_any_terminated(
        js, jobs, DRMAA2_INFINITE_TIME);
    printf("returned %s %x\n", res2->id, res2);
    long found = -1;
    for (long del_idx=0; del_idx < job_cnt; del_idx++) {
        const drmaa2_j candidate =
            (const drmaa2_j) drmaa2_list_get(jobs, del_idx);
        // Look, the pointers are the same. No need to compare values.
        if (candidate == res2) {
            found = del_idx;
            break;
        }
    }
    if (found != -1) {
      drmaa2_list_del(jobs, found);
    } else {
      printf("Couldn't find job\n");
      return 3;
    }
    job_cnt = drmaa2_list_size(jobs);
  }

  printf("Freeing things a\n");
  drmaa2_j_free(&a);
  printf("Freeing things b\n");
  drmaa2_j_free(&b);
  printf("Freeing things list args\n");
  // The args are owned by the template. If you free these, then
  // freeing the job template causes a sigsegv.
  // drmaa2_list_free(&args);
  //free(remote_command);
  printf("Freeing things template\n");
  drmaa2_jtemplate_free(&jt);

  printf("Close\n");
  drmaa2_close_jsession(js);
  printf("Free\n");
  drmaa2_jsession_free(&js);
  printf("Destroy\n");
  drmaa2_destroy_jsession(name);
  return 0;
}

#include <time.h>
int main(int argc, char** argv) {
  int s = sizeof(time_t);
  printf("time_t is size %d\n", s);
  return job_with_hold();
}
