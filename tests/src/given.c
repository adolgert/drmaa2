#include <string.h>
#include <stdio.h>
#include <drmaa2.h>

int main(int argc, char** argv) {
       /* Create and open a new job session. */
       drmaa2_jsession js = drmaa2_create_jsession("test_session", NULL);
       drmaa2_j job = NULL;
       drmaa2_jtemplate jt = NULL;

       if (js != NULL) {
          /* create a new job template. */
          jt = drmaa2_jtemplate_create();

          /* add the job characteristics */
          jt->jobName = strdup("test_job");
          jt->remoteCommand = strdup("sleep");
          /* since no allocated strings are used we don´t need to specify a callback */
          drmaa2_string_list args = drmaa2_list_create(DRMAA2_STRINGLIST, NULL);
          drmaa2_list_add(args, "60");
          jt->args = args;

          /* submit the jobs */
          job = drmaa2_jsession_run_job(js, jt);
       }

       drmaa2_j_free(&job);
       drmaa2_jtemplate_free(&jt);
       return 0;
}
