from src.validation import validate_contact, validate_details


def test_contact_accepts_email_and_phone():
    assert validate_contact("client@example.com")
    assert validate_contact("+7 (999) 123-45-67")
    assert validate_contact("1234567")


def test_contact_rejects_invalid_or_empty_values():
    assert not validate_contact("")
    assert not validate_contact("not a contact")
    assert not validate_contact("x" * 121)
    assert not validate_contact("-------")
    assert not validate_contact("+++++++")
    assert not validate_contact("123456")
    assert not validate_contact("1234567890123456")
    assert not validate_contact("1234567abc")


def test_details_length_boundaries():
    assert validate_details("Нужен бот для записи клиентов")[0]
    assert not validate_details("Коротко")[0]
    assert not validate_details("x" * 1001)[0]
