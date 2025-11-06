import bcrypt

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

if __name__ == "__main__":
    password = input("Enter password to hash: ")
    hashed = hash_password(password)
    print(f"\nHashed password:\n{hashed}")
    print("\nAdd this to your config.yaml file for the user's password field.")