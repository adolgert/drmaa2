from setuptools import setup

setup(name="drmaa",
      version="0.1",
      description="Wrapper for DRMAA2 library",
      url="https://stash.ihme.washington.edu/users/adolgert/repos/drmaa2/browse",
      author="Andrew Dolgert",
      author_email="adolgert@uw.edu",
      license="Apache 3.0",
      packages=["drmaa2"],
      install_requires=[],
      test_suite="py.test",
      tests_require="pytest",
      zip_safe=True)
