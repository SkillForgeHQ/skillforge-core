# api/utils/crypto.py
from jwcrypto import jwk
import json

# Generate a new Elliptic Curve key pair (ES256 is a common, strong algorithm)
key = jwk.JWK.generate(kty="EC", crv="P-256")

# The private key should be kept secret (e.g., in an environment variable)
# The public key can be shared openly so others can verify your signatures
private_key_json = key.export_private()
public_key_json = key.export_public()

# Save them to files for now
with open("private_key.json", "w") as f:
    f.write(private_key_json)

with open("public_key.json", "w") as f:
    f.write(public_key_json)

print("✅ Private and public keys generated and saved.")
print("Public Key JWK:", public_key_json)
