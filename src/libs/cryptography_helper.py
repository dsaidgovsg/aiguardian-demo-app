import base64
import hashlib


def hash(plaintext):
    return base64.b64encode(
        hashlib.sha256(plaintext.encode("utf-8")).digest()
    ).decode("utf-8")


if __name__ == "__main__":
    import sys
    from getpass import getpass

    t = sys.argv[1] if len(sys.argv) > 1 else getpass("Enter plaintext: ")
    print("Hashed value: ", hash(t))
