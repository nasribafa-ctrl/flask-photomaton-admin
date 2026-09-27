from werkzeug.security import check_password_hash, generate_password_hash

# Demo hash generated on the fly (never a real account's hash) to illustrate the check.
password_tape = "admin123"
hash_en_base = generate_password_hash(password_tape)

# La vérification
if check_password_hash(hash_en_base, password_tape):
    print("✅ C'est le bon mot de passe !")
else:
    print("❌ Mot de passe incorrect ou hash corrompu.")