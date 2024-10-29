import base64
import hashlib
import json
import secrets
import string
import uuid
from typing import Dict


def hash(plaintext):
    return base64.b64encode(
        hashlib.sha256(plaintext.encode("utf-8")).digest()
    ).decode("utf-8")


def hash_base32(plaintext):
    return base64.b32encode(
        hashlib.sha256(plaintext.encode("utf-8")).digest()
    ).decode("utf-8")


def generate_uuid(text):
    """Generate a consistent uuid based on given text"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, text))


def generate_random_string(length: int, characters: str = ""):
    """
    Generate a random string of given length and set of characters
    Default to alphanumeric characters.
    """
    characters = characters or string.ascii_letters + string.digits
    return "".join(secrets.choice(characters) for _ in range(length))


def decode_jwt_payload(jwt_token: str) -> Dict:
    """Decode the raw JWT payload, no signature verification involved.
    Only use this if the JWT token has been verified."""
    # Split the JWT token into its three parts
    parts = jwt_token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format")

    # Decode the payload (the second part of the token)
    payload_encoded = parts[1]

    # Add necessary padding to the payload for base64 decoding
    payload_encoded += "=" * (-len(payload_encoded) % 4)

    # Decode the payload from base64
    payload_decoded = base64.urlsafe_b64decode(payload_encoded)

    # Convert the decoded payload from JSON to a Python dictionary
    payload_dict = json.loads(payload_decoded)

    return payload_dict


if __name__ == "__main__":
    from getpass import getpass

    t = getpass("Enter plaintext: ")
    print("Hashed value: ", hash(t))
    print("UUID value: ", generate_uuid(t))
    print("Rand value: ", len(t), generate_random_string(len(t)))
