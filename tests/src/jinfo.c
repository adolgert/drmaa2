#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <drmaa2.h>


void job_info_try() {
  drmaa2_jinfo ji = drmaa2_jinfo_create();
  printf("jinfo pointer %0x\n", ji);
  printf("jinfo jobId pointer %0x\n", ji->jobId);
  char* job_id = (char*) malloc(256);
  strcpy(job_id, "1234");
  ji->jobId = job_id;
  ji->jobId = 0;
  free(job_id);
  drmaa2_jinfo_free(&ji);
}


void job_info_fail() {
  drmaa2_jinfo ji = drmaa2_jinfo_create();
  printf("jinfo pointer %0x\n", ji);
  printf("jinfo jobId pointer %0x\n", ji->jobId);
  char* job_id = (char*) malloc(256);
  strcpy(job_id, "1234");
  ji->jobId = job_id;
  drmaa2_jinfo_free(&ji);
  free(job_id);
}


int main(int argc, char* argv[]) {
  job_info_try();
  job_info_fail();
  return 0;
}
