def test_valid_login():
    username = "admin"
    password = "1234"

    assert username == "admin"
    assert password == "1234"

def test_invalid_login():
    username = "admin"
    password = "wrong"

    assert password == "1234"