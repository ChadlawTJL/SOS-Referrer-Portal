from werkzeug.security import generate_password_hash

test_password = "November!"
password_hash = generate_password_hash(
    test_password,
    method="scrypt"
)

print(password_hash)
