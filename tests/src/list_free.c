/* Both of these examples are OK.
 * That means that when you pass in no deallocator
 * the library doesn't attempt to free a pointer you created.
 */
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <drmaa2.h>

void mdealloc(void** value) {
  free(*value);
}

void list_free_explicit() {
  drmaa2_string_list l = drmaa2_list_create(DRMAA2_STRINGLIST,
					    (drmaa2_list_entryfree) 0);
  const int job_cnt = 10000;
  char* jobs[job_cnt];
  for (int m_idx=0; m_idx<job_cnt; ++m_idx) {
    jobs[m_idx] = malloc(5);
    strcpy(jobs[m_idx], "123");
    drmaa2_list_add(l, jobs[m_idx]);
  }
  drmaa2_list_free(&l);
  for (int f=0; f<job_cnt; ++f) {
    free(jobs[f]);
  }
}


void list_free_good() {
  drmaa2_string_list l = drmaa2_list_create(DRMAA2_STRINGLIST,
				     (drmaa2_list_entryfree) mdealloc);
  char* job1 = malloc(5);
  strcpy(job1, "123");
  drmaa2_list_add(l, job1);
  drmaa2_list_free(&l);
}


int main(int argc, char* argv[]) {
  list_free_good();
  printf("finished good part.\n");
  list_free_explicit();
  return 0;
}
