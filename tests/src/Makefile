# export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$SGE_ROOT/lib/lx-amd64
example: example.c
	gcc -I$(SGE_ROOT)/include -L$(SGE_ROOT)/lib/lx-amd64 example.c -o example -ldrmaa2

hold: hold.c
	gcc -std=c99 -g -I$(SGE_ROOT)/include -L$(SGE_ROOT)/lib/lx-amd64 hold.c -o hold -ldrmaa2

given: given.c
	gcc -g -I$(SGE_ROOT)/include -L$(SGE_ROOT)/lib/lx-amd64 given.c -o given -ldrmaa2
