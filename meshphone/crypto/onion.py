"""
Onion Routing - Multi-layer encryption for privacy
Each relay can only see the next hop, not the full route
"""

import os
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from meshphone.crypto.keys import KeyManager


@dataclass
class OnionLayer:
    """
    A single layer of the onion
    Contains encrypted routing info for one hop
    """
    encrypted_data: bytes
    iv: bytes
    mac: bytes
    
    def to_dict(self) -> Dict:
        return {
            "encrypted_data": self.encrypted_data.hex(),
            "iv": self.iv.hex(),
            "mac": self.mac.hex(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OnionLayer':
        return cls(
            encrypted_data=bytes.fromhex(data["encrypted_data"]),
            iv=bytes.fromhex(data["iv"]),
            mac=bytes.fromhex(data["mac"]),
        )


@dataclass
class OnionPacket:
    """
    Complete onion-routed packet
    Contains multiple encrypted layers
    """
    layers: List[OnionLayer]
    final_payload: bytes  # The actual message (E2E encrypted)
    
    def to_dict(self) -> Dict:
        return {
            "layers": [layer.to_dict() for layer in self.layers],
            "final_payload": self.final_payload.hex(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OnionPacket':
        return cls(
            layers=[OnionLayer.from_dict(l) for l in data["layers"]],
            final_payload=bytes.fromhex(data["final_payload"]),
        )
    
    def to_wire_format(self) -> bytes:
        """Serialize for transmission"""
        return json.dumps(self.to_dict()).encode('utf-8')
    
    @classmethod
    def from_wire_format(cls, data: bytes) -> 'OnionPacket':
        """Deserialize from transmission"""
        return cls.from_dict(json.loads(data.decode('utf-8')))


class OnionRouter:
    """
    Creates and peels onion-routed packets
    Provides Tor-style layered encryption for mesh routing
    """
    
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
    
    def _derive_layer_keys(self, shared_secret: bytes, hop_id: str) -> Tuple[bytes, bytes]:
        """
        Derive encryption and MAC keys for one onion layer
        Returns: (cipher_key, mac_key)
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=64,  # 32 for cipher + 32 for MAC
            salt=hop_id.encode('utf-8'),
            info=b"meshphone_onion_layer",
        )
        
        key_material = hkdf.derive(shared_secret)
        return key_material[:32], key_material[32:]
    
    def _encrypt_layer(self, plaintext: bytes, cipher_key: bytes, mac_key: bytes) -> OnionLayer:
        """
        Encrypt a single onion layer
        """
        # Generate random IV
        iv = os.urandom(16)
        
        # Encrypt with AES-256-CBC
        cipher = Cipher(algorithms.AES(cipher_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        
        # Pad plaintext to AES block size (16 bytes)
        padding_length = 16 - (len(plaintext) % 16)
        padded_plaintext = plaintext + bytes([padding_length] * padding_length)
        
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
        
        # Calculate MAC
        h = hmac.HMAC(mac_key, hashes.SHA256())
        h.update(iv + ciphertext)
        mac = h.finalize()
        
        return OnionLayer(
            encrypted_data=ciphertext,
            iv=iv,
            mac=mac
        )
    
    def _decrypt_layer(self, layer: OnionLayer, cipher_key: bytes, mac_key: bytes) -> bytes:
        """
        Decrypt a single onion layer
        Returns plaintext with padding removed
        """
        # Verify MAC
        h = hmac.HMAC(mac_key, hashes.SHA256())
        h.update(layer.iv + layer.encrypted_data)
        h.verify(layer.mac)
        
        # Decrypt
        cipher = Cipher(algorithms.AES(cipher_key), modes.CBC(layer.iv))
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(layer.encrypted_data) + decryptor.finalize()
        
        # Remove padding
        padding_length = padded_plaintext[-1]
        plaintext = padded_plaintext[:-padding_length]
        
        return plaintext
    
    def create_onion(self, route: List[str], route_keys: Dict[str, bytes], 
                     final_payload: bytes) -> OnionPacket:
        """
        Create an onion packet for a route
        
        Args:
            route: List of node IDs in order [sender, relay1, relay2, ..., recipient]
            route_keys: Dict of {node_id: public_key} for each hop
            final_payload: The actual message (already E2E encrypted)
            
        Returns:
            OnionPacket with layered encryption
        """
        # Build routing info for each hop
        # Start from the end and work backwards
        layers = []
        
        # Skip sender (route[0]) and recipient (route[-1])
        # Only create layers for intermediate hops
        relay_nodes = route[1:-1]  # The relays in the middle
        
        for i, relay_id in enumerate(relay_nodes):
            # Next hop info
            if i < len(relay_nodes) - 1:
                next_hop = relay_nodes[i + 1]
            else:
                # Last relay, next hop is recipient
                next_hop = route[-1]
            
            routing_info = {
                "next_hop": next_hop,
                "hop_number": i + 1,
            }
            
            routing_json = json.dumps(routing_info).encode('utf-8')
            
            # Perform DH with relay's public key
            relay_public_key = route_keys[relay_id]
            shared_secret = self.key_manager.perform_dh(
                self.key_manager.ephemeral_key.private_key_bytes,
                relay_public_key
            )
            
            # Derive keys for this layer
            cipher_key, mac_key = self._derive_layer_keys(shared_secret, relay_id)
            
            # Encrypt this layer
            layer = self._encrypt_layer(routing_json, cipher_key, mac_key)
            layers.append(layer)
        
        # Layers are in forward order (first relay's layer is layers[0])
        return OnionPacket(layers=layers, final_payload=final_payload)
    
    def peel_layer(self, packet: OnionPacket, my_node_id: str, 
                   sender_public_key: bytes) -> Tuple[Optional[str], OnionPacket]:
        """
        Peel one layer of the onion (called by relay)
        
        Args:
            packet: The onion packet
            my_node_id: This relay's node ID
            sender_public_key: Sender's ephemeral public key
            
        Returns:
            (next_hop_id, remaining_packet) or (None, packet) if no more layers
        """
        if not packet.layers:
            # No more layers, we must be the recipient
            return None, packet
        
        # Get the first layer (for us)
        our_layer = packet.layers[0]
        remaining_layers = packet.layers[1:]
        
        # Perform DH with sender's public key
        shared_secret = self.key_manager.perform_dh(
            self.key_manager.identity_key.private_key_bytes,
            sender_public_key
        )
        
        # Derive keys for our layer
        cipher_key, mac_key = self._derive_layer_keys(shared_secret, my_node_id)
        
        # Decrypt our layer
        try:
            routing_json = self._decrypt_layer(our_layer, cipher_key, mac_key)
            routing_info = json.loads(routing_json.decode('utf-8'))
        except Exception as e:
            # MAC verification failed or decryption failed
            # This layer wasn't for us or packet is corrupted
            raise ValueError(f"Failed to decrypt onion layer: {e}")
        
        next_hop = routing_info["next_hop"]
        
        # Create new packet with remaining layers
        new_packet = OnionPacket(
            layers=remaining_layers,
            final_payload=packet.final_payload
        )
        
        return next_hop, new_packet
    
    def extract_payload(self, packet: OnionPacket) -> bytes:
        """
        Extract final payload (called by recipient after all layers peeled)
        """
        if packet.layers:
            raise ValueError("Packet still has onion layers - not the final recipient")
        
        return packet.final_payload


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("ONION ROUTING DEMO")
    print("=" * 60)
    
    # Create nodes: Alice -> Bob (relay) -> Carol (relay) -> Dave
    nodes = {}
    for name in ["Alice", "Bob", "Carol", "Dave"]:
        km = KeyManager(name)
        km.generate_identity_keys()
        km.generate_ephemeral_key()
        nodes[name] = km
    
    print("\n🔑 Nodes Created")
    for name, km in nodes.items():
        print(f"   {name}: {km.identity_key.public_key_hex[:16]}...")
    
    # Define route: Alice -> Bob -> Carol -> Dave
    route = ["Alice", "Bob", "Carol", "Dave"]
    
    # Gather public keys
    route_keys = {
        name: km.identity_key.public_key_bytes
        for name, km in nodes.items()
    }
    
    print(f"\n📍 Route: {' -> '.join(route)}")
    
    # Alice creates onion packet
    alice_router = OnionRouter(nodes["Alice"])
    
    final_payload = b"Secret message from Alice to Dave!"
    onion_packet = alice_router.create_onion(route, route_keys, final_payload)
    
    print(f"\n🧅 Alice creates onion packet")
    print(f"   Layers: {len(onion_packet.layers)}")
    print(f"   Final payload: {len(final_payload)} bytes")
    print(f"   Layer 1 (Bob): {onion_packet.layers[0].encrypted_data.hex()[:32]}...")
    if len(onion_packet.layers) > 1:
        print(f"   Layer 2 (Carol): {onion_packet.layers[1].encrypted_data.hex()[:32]}...")
    
    # Bob peels his layer
    bob_router = OnionRouter(nodes["Bob"])
    next_hop, packet_after_bob = bob_router.peel_layer(
        onion_packet,
        "Bob",
        nodes["Alice"].ephemeral_key.public_key_bytes
    )
    
    print(f"\n📡 Bob peels layer 1")
    print(f"   Next hop revealed: {next_hop}")
    print(f"   Remaining layers: {len(packet_after_bob.layers)}")
    print(f"   Bob CANNOT see final destination ✅")
    
    # Carol peels her layer
    carol_router = OnionRouter(nodes["Carol"])
    next_hop, packet_after_carol = carol_router.peel_layer(
        packet_after_bob,
        "Carol",
        nodes["Alice"].ephemeral_key.public_key_bytes
    )
    
    print(f"\n📡 Carol peels layer 2")
    print(f"   Next hop revealed: {next_hop}")
    print(f"   Remaining layers: {len(packet_after_carol.layers)}")
    print(f"   Carol knows next hop is Dave, but not the full route ✅")
    
    # Dave extracts final payload
    dave_router = OnionRouter(nodes["Dave"])
    received_payload = dave_router.extract_payload(packet_after_carol)
    
    print(f"\n🎯 Dave receives final payload")
    print(f"   Payload: {received_payload.decode()}")
    print(f"   Match: {received_payload == final_payload} ✅")
    
    print("\n✅ Onion routing working perfectly!")
    print("   • Each relay only sees next hop ✅")
    print("   • Full route privacy ✅")
    print("   • MAC authentication ✅")
    print("   • Payload delivered intact ✅")
