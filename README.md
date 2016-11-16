Drew Dolgert, IHME, adolgert@uw.edu


This repository is a test of the C interface to DRMAA2 on the
cluster. There is a Python library which wraps the DRMAA v1 interface,
but we have the DRMAA2 interface installed, so this checks out some
of the features.

## What is DRMAA2?

* Open Grid Forum document [GFD.194.pdf](https://www.ogf.org/ogf/doku.php/documents/documents)
* [Daniel Gruber's blog](http://www.gridengine.eu/index.php/programming-apis/178-the-drmaa2-tutorial-introduction-1-2013-10-05)
* On the cluster, man pages: man -M $SGE_ROOT/man drmaa2_open_jsession

## Requirements

* Tested only on Python 3.5, 3.6 so far.
* Needs an installation of DRMAA2 to run. (Univa Grid Engine, for instance)
* No non-default Python libraries used.
* Can build docs with Sphinx.
* Can run tests with pytest.

## Building Docs:

	git clone https://adolgert@stash.ihme.washington.edu/scm/~adolgert/drmaa2.git
	cd drmaa2/docs
	make html
	firefox _build/html/index.html
