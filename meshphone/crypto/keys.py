"""
Key Management - Generate, store, and exchange cryptographic keys
Uses X25519 for key exchange, Ed25519 for signing
"""

import os
import json
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


@dataclass
class KeyPair:
    """A cryptographic key pair"""
    private_key_bytes: bytes
    public_key_bytes: bytes
    key_type: str  # "x25519" or "ed25519"
    
    def to_dict(self) -> Dict:
        return {
            "public_key": self.public_key_bytes.hex(),
            "key_type": self.key_type,
        }
    
    @property
    def public_key_hex(self) -> str:
        return self.public_key_bytes.hex()
    
    @property
    def private_key_hex(self) -> str:
        return self.private_key_bytes.hex()


class KeyManager:
    """
    Manages cryptographic keys for a mesh node
    Handles key generation, storage, and Diffie-Hellman exchange
    """
    
    def __init__(self, node_id: str, storage_path: Optional[Path] = None):
        self.node_id = node_id
        self.storage_path = storage_path or Path(f".meshphone/keys/{node_id}")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Identity keys (long-term)
        self.identity_key: Optional[KeyPair] = None
        self.signing_key: Optional[KeyPair] = None
        
        # Ephemeral keys (short-term, rotated)
        self.ephemeral_key: Optional[KeyPair] = None
        
        # Prekeys for async messaging
        self.prekeys: Dict[int, KeyPair] = {}
        
        # Peer public keys (for encryption to others)
        self.peer_keys: Dict[str, bytes] = {}
        
    def generate_identity_keys(self) -> Tuple[KeyPair, KeyPair]:
        """
        Generate long-term identity keys
        Returns: (encryption_keypair, signing_keypair)
        """
        # X25519 for encryption/key exchange
        x25519_private = X25519PrivateKey.generate()
        x25519_public = x25519_private.public_key()
        
        encryption_keypair = KeyPair(
            private_key_bytes=x25519_private.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            ),
            public_key_bytes=x25519_public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            ),
            key_type="x25519"
        )
        
        # Ed25519 for signing
        ed25519_private = Ed25519PrivateKey.generate()
        ed25519_public = ed25519_private.public_key()
        
        signing_keypair = KeyPair(
            private_key_bytes=ed25519_private.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            ),
            public_key_bytes=ed25519_public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            ),
            key_type="ed25519"
        )
        
        self.identity_key = encryption_keypair
        self.signing_key = signing_keypair
        
        return encryption_keypair, signing_keypair
    
    def generate_ephemeral_key(self) -> KeyPair:
        """Generate short-term ephemeral key (rotated per session)"""
        x25519_private = X25519PrivateKey.generate()
        x25519_public = x25519_private.public_key()
        
        ephemeral_keypair = KeyPair(
            private_key_bytes=x25519_private.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            ),
            public_key_bytes=x25519_public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            ),
            key_type="x25519"
        )
        
        self.ephemeral_key = ephemeral_keypair
        return ephemeral_keypair
    
    def generate_prekeys(self, count: int = 10) -> Dict[int, KeyPair]:
        """
        Generate prekeys for asynchronous messaging
        Allows others to encrypt to us even when offline
        """
        self.prekeys = {}
        
        for i in range(count):
            x25519_private = X25519PrivateKey.generate()
            x25519_public = x25519_private.public_key()
            
            prekey = KeyPair(
                private_key_bytes=x25519_private.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption()
                ),
                public_key_bytes=x25519_public.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                ),
                key_type="x25519"
            )
            
            self.prekeys[i] = prekey
        
        return self.prekeys
    
    def perform_dh(self, our_private: bytes, their_public: bytes) -> bytes:
        """
        Perform Diffie-Hellman key exchange
        Returns shared secret (32 bytes)
        """
        private_key = X25519PrivateKey.from_private_bytes(our_private)
        public_key = X25519PublicKey.from_public_bytes(their_public)
        
        shared_secret = private_key.exchange(public_key)
        return shared_secret
    
    def derive_keys(self, shared_secret: bytes, info: bytes = b"meshphone") -> Tuple[bytes, bytes]:
        """
        Derive encryption and MAC keys from shared secret using HKDF
        Returns: (encryption_key, mac_key) each 32 bytes
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=64,  # 32 bytes for encryption + 32 for MAC
            salt=None,
            info=info,
        )
        
        key_material = hkdf.derive(shared_secret)
        
        encryption_key = key_material[:32]
        mac_key = key_material[32:]
        
        return encryption_key, mac_key
    
    def add_peer_key(self, peer_id: str, public_key: bytes):
        """Store a peer's public key for future encryption"""
        self.peer_keys[peer_id] = public_key
    
    def get_peer_key(self, peer_id: str) -> Optional[bytes]:
        """Retrieve a peer's public key"""
        return self.peer_keys.get(peer_id)
    
    def save_keys(self):
        """Save keys to disk (encrypted in production)"""
        if not self.identity_key or not self.signing_key:
            return
        
        keys_data = {
            "node_id": self.node_id,
            "identity_key": {
                "public": self.identity_key.public_key_hex,
                "private": self.identity_key.private_key_hex,
            },
            "signing_key": {
                "public": self.signing_key.public_key_hex,
                "private": self.signing_key.private_key_hex,
            },
            "ephemeral_key": {
                "public": self.ephemeral_key.public_key_hex if self.ephemeral_key else None,
                "private": self.ephemeral_key.private_key_hex if self.ephemeral_key else None,
            } if self.ephemeral_key else None,
            "prekeys": {
                i: {"public": kp.public_key_hex, "private": kp.private_key_hex}
                for i, kp in self.prekeys.items()
            },
            "peer_keys": {
                peer_id: key.hex()
                for peer_id, key in self.peer_keys.items()
            }
        }
        
        keys_file = self.storage_path / "keys.json"
        with open(keys_file, 'w') as f:
            json.dump(keys_data, f, indent=2)
    
    def load_keys(self) -> bool:
        """Load keys from disk"""
        keys_file = self.storage_path / "keys.json"
        
        if not keys_file.exists():
            return False
        
        with open(keys_file, 'r') as f:
            keys_data = json.load(f)
        
        # Load identity key
        self.identity_key = KeyPair(
            private_key_bytes=bytes.fromhex(keys_data["identity_key"]["private"]),
            public_key_bytes=bytes.fromhex(keys_data["identity_key"]["public"]),
            key_type="x25519"
        )
        
        # Load signing key
        self.signing_key = KeyPair(
            private_key_bytes=bytes.fromhex(keys_data["signing_key"]["private"]),
            public_key_bytes=bytes.fromhex(keys_data["signing_key"]["public"]),
            key_type="ed25519"
        )
        
        # Load ephemeral key if exists
        if keys_data.get("ephemeral_key"):
            self.ephemeral_key = KeyPair(
                private_key_bytes=bytes.fromhex(keys_data["ephemeral_key"]["private"]),
                public_key_bytes=bytes.fromhex(keys_data["ephemeral_key"]["public"]),
                key_type="x25519"
            )
        
        # Load prekeys
        for i_str, prekey_data in keys_data.get("prekeys", {}).items():
            i = int(i_str)
            self.prekeys[i] = KeyPair(
                private_key_bytes=bytes.fromhex(prekey_data["private"]),
                public_key_bytes=bytes.fromhex(prekey_data["public"]),
                key_type="x25519"
            )
        
        # Load peer keys
        for peer_id, key_hex in keys_data.get("peer_keys", {}).items():
            self.peer_keys[peer_id] = bytes.fromhex(key_hex)
        
        return True
    
    def get_public_bundle(self) -> Dict:
        """
        Get public key bundle to share with others
        This is what gets advertised in the mesh
        """
        if not self.identity_key or not self.signing_key:
            raise ValueError("Keys not generated yet")
        
        return {
            "node_id": self.node_id,
            "identity_key": self.identity_key.public_key_hex,
            "signing_key": self.signing_key.public_key_hex,
            "ephemeral_key": self.ephemeral_key.public_key_hex if self.ephemeral_key else None,
            "prekeys": {
                i: kp.public_key_hex
                for i, kp in self.prekeys.items()
            }
        }


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("KEY MANAGEMENT DEMO")
    print("=" * 60)
    
    # Alice generates keys
    alice_km = KeyManager("Alice")
    alice_identity, alice_signing = alice_km.generate_identity_keys()
    alice_km.generate_ephemeral_key()
    alice_km.generate_prekeys(count=5)
    
    print("\n🔑 Alice's Keys Generated")
    print(f"   Identity (public): {alice_identity.public_key_hex[:16]}...")
    print(f"   Signing (public): {alice_signing.public_key_hex[:16]}...")
    print(f"   Prekeys: {len(alice_km.prekeys)}")
    
    # Bob generates keys
    bob_km = KeyManager("Bob")
    bob_identity, bob_signing = bob_km.generate_identity_keys()
    
    print("\n🔑 Bob's Keys Generated")
    print(f"   Identity (public): {bob_identity.public_key_hex[:16]}...")
    
    # Key exchange (Diffie-Hellman)
    print("\n🤝 Performing Key Exchange")
    
    # Alice computes shared secret with Bob
    alice_shared = alice_km.perform_dh(
        alice_identity.private_key_bytes,
        bob_identity.public_key_bytes
    )
    
    # Bob computes shared secret with Alice
    bob_shared = bob_km.perform_dh(
        bob_identity.private_key_bytes,
        alice_identity.public_key_bytes
    )
    
    # Both should have same shared secret
    print(f"   Alice's shared secret: {alice_shared.hex()[:32]}...")
    print(f"   Bob's shared secret:   {bob_shared.hex()[:32]}...")
    print(f"   Secrets match: {alice_shared == bob_shared} ✅")
    
    # Derive encryption keys
    alice_enc, alice_mac = alice_km.derive_keys(alice_shared)
    bob_enc, bob_mac = bob_km.derive_keys(bob_shared)
    
    print(f"\n🔐 Derived Keys Match: {alice_enc == bob_enc} ✅")
    
    # Save Alice's keys
    alice_km.save_keys()
    print(f"\n💾 Keys saved to: {alice_km.storage_path}")
    
    # Export public bundle (for sharing)
    alice_bundle = alice_km.get_public_bundle()
    print(f"\n📦 Alice's Public Bundle:")
    print(f"   Node ID: {alice_bundle['node_id']}")
    print(f"   Identity Key: {alice_bundle['identity_key'][:16]}...")
    print(f"   Prekeys: {len(alice_bundle['prekeys'])}")
    
    print("\n✅ Key management complete!")
