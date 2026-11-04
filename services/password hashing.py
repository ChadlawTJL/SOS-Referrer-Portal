from werkzeug.security import generate_password_hash

test_password = "Test"
password_hash = generate_password_hash(
    test_password,
    method="scrypt"
)

print(password_hash)
