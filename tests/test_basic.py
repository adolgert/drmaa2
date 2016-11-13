import drmaa2.session as drmaa2


def test_manager():
    assert drmaa2.drmsName
    assert len(drmaa2.drmsName) > 0
    assert isinstance(drmaa2.drmsName, str)
    assert drmaa2.drmsVersion
    assert isinstance(drmaa2.drmsVersion[0], str)
    assert isinstance(drmaa2.drmsVersion[1], str)
    print(drmaa2.drmsName)
    print(drmaa2.drmsVersion)
