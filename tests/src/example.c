#include <string.h>
#include <stdio.h>
#include <drmaa2.h>


int create_destroy() {
  drmaa2_jsession js;
  drmaa2_string error;

  char name[]="adolgert1";
  js = drmaa2_create_jsession(name, NULL);
  if (NULL == js) {
    printf("error %d\n", drmaa2_lasterror());
    error = (drmaa2_string) drmaa2_lasterror_text();
    printf("Could not create session. %s\n", error);
    drmaa2_string_free(&error);
    return 1;
  }

  printf("Close\n");
  drmaa2_close_jsession(js);
  printf("Free\n");
  drmaa2_jsession_free(&js);
  printf("Destroy\n");
  drmaa2_destroy_jsession(name);
  return 0;
}


int open_and_destroy(const char* name) {
  drmaa2_jsession js;
  drmaa2_string error;

  js = drmaa2_open_jsession(name);
  if (NULL == js) {
    printf("error %d\n", drmaa2_lasterror());
    error = (drmaa2_string) drmaa2_lasterror_text();
    printf("Could not create session. %s\n", error);
    drmaa2_string_free(&error);
    return 1;
  }

  printf("Close\n");
  drmaa2_close_jsession(js);
  printf("Free\n");
  drmaa2_jsession_free(&js);
  printf("Destroy\n");
  drmaa2_destroy_jsession(name);
}


void destroy_my_sessions() {
  long js_idx = 0;
  long available = 0;
  drmaa2_error retval;
  drmaa2_string error;

  drmaa2_string_list sessions = drmaa2_get_jsession_names();
  drmaa2_jsession jsession;

  for (js_idx=0; js_idx<drmaa2_list_size(sessions); js_idx++) {
    const char* session = drmaa2_list_get(sessions, js_idx);
    printf("Checking session %s\n", session);
    if (strncmp(session, "adolgert", sizeof("adolgert")-1) == 0) {
      char* atchar = strchr(session, '@');
      char* name = atchar+1;
      printf("Found session %s\n", name);
      retval = drmaa2_destroy_jsession(name);
      if (DRMAA2_SUCCESS != retval) {
        printf("error %d\n", retval);
        error = (drmaa2_string) drmaa2_lasterror_text();
        printf("Could not destroy session. %s\n", error);
        drmaa2_string_free(&error);
      }
    }
  }

  drmaa2_list_free(&sessions);
}


int main(int argc, char** argv) {
  destroy_my_sessions();
  return 0;
}
