# export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$SGE_ROOT/lib/lx-amd64
example: example.c
	gcc -I$(SGE_ROOT)/include -L$(SGE_ROOT)/lib/lx-amd64 example.c -o example -ldrmaa2
