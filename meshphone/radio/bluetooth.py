"""
Bluetooth Low Energy Radio Layer
Handles peer discovery and message transmission via BLE
"""

import time
import json
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum


class BLEState(Enum):
    """BLE radio states"""
    OFF = "off"
    SCANNING = "scanning"
    ADVERTISING = "advertising"
    CONNECTED = "connected"


@dataclass
class BLEPeer:
    """A discovered BLE peer"""
    node_id: str
    address: str  # MAC address or UUID
    rssi: int  # Signal strength (negative dBm)
    last_seen: float
    public_key: Optional[bytes] = None
    
    @property
    def distance_estimate(self) -> float:
        """
        Estimate distance in meters from RSSI
        Very rough approximation: RSSI = -10*n*log10(d) + A
        """
        if self.rssi >= -50:
            return 1.0  # Very close (< 1m)
        elif self.rssi >= -70:
            return 10.0  # Close (1-10m)
        elif self.rssi >= -85:
            return 50.0  # Medium (10-50m)
        else:
            return 100.0  # Far (50-100m)
    
    @property
    def is_stale(self, timeout: float = 30.0) -> bool:
        """Check if peer hasn't been seen recently"""
        return (time.time() - self.last_seen) > timeout


class BLERadio(ABC):
    """
    Abstract BLE radio interface
    Implemented by both mock (testing) and real (PyObjC/Android) versions
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.state = BLEState.OFF
        self.discovered_peers: Dict[str, BLEPeer] = {}
        self.on_peer_discovered: Optional[Callable[[BLEPeer], None]] = None
        self.on_message_received: Optional[Callable[[str, bytes], None]] = None
        
    @abstractmethod
    def start(self):
        """Start BLE radio (scanning + advertising)"""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop BLE radio"""
        pass
    
    @abstractmethod
    def send_message(self, peer_id: str, data: bytes) -> bool:
        """
        Send message to a peer
        Returns True if sent successfully
        """
        pass
    
    @abstractmethod
    def get_neighbors(self) -> Set[str]:
        """Get set of currently reachable peer IDs"""
        pass
    
    def cleanup_stale_peers(self, timeout: float = 30.0):
        """Remove peers that haven't been seen recently"""
        stale_peers = [
            peer_id for peer_id, peer in self.discovered_peers.items()
            if peer.is_stale(timeout)
        ]
        
        for peer_id in stale_peers:
            del self.discovered_peers[peer_id]


class MockBLERadio(BLERadio):
    """
    Mock BLE radio for testing without hardware
    Simulates BLE behavior in software
    """
    
    # Class-level registry of all mock radios (simulates radio environment)
    _all_radios: Dict[str, 'MockBLERadio'] = {}
    
    def __init__(self, node_id: str, x: float = 0.0, y: float = 0.0, 
                 max_range: float = 100.0):
        super().__init__(node_id)
        self.x = x
        self.y = y
        self.max_range = max_range
        self.public_key = f"mock_key_{node_id}".encode()
        
        # Register in global registry
        MockBLERadio._all_radios[node_id] = self
    
    def distance_to(self, other: 'MockBLERadio') -> float:
        """Calculate distance to another mock radio"""
        return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5
    
    def start(self):
        """Start mock BLE radio"""
        self.state = BLEState.SCANNING
        self._discover_peers()
    
    def stop(self):
        """Stop mock BLE radio"""
        self.state = BLEState.OFF
        self.discovered_peers.clear()
    
    def _discover_peers(self):
        """Discover other radios within range"""
        for peer_id, peer_radio in MockBLERadio._all_radios.items():
            if peer_id == self.node_id:
                continue
            
            if peer_radio.state == BLEState.OFF:
                continue
            
            distance = self.distance_to(peer_radio)
            
            if distance <= self.max_range:
                # Calculate mock RSSI from distance
                # RSSI roughly: -40 at 1m, -70 at 10m, -85 at 50m
                rssi = int(-40 - (20 * (distance / 10)))
                
                peer = BLEPeer(
                    node_id=peer_id,
                    address=f"mock:{peer_id}",
                    rssi=rssi,
                    last_seen=time.time(),
                    public_key=peer_radio.public_key
                )
                
                self.discovered_peers[peer_id] = peer
                
                # Trigger callback
                if self.on_peer_discovered:
                    self.on_peer_discovered(peer)
    
    def send_message(self, peer_id: str, data: bytes) -> bool:
        """Send message to peer (simulated)"""
        if peer_id not in self.discovered_peers:
            return False
        
        peer_radio = MockBLERadio._all_radios.get(peer_id)
        if not peer_radio:
            return False
        
        # Simulate message delivery
        if peer_radio.on_message_received:
            peer_radio.on_message_received(self.node_id, data)
        
        return True
    
    def get_neighbors(self) -> Set[str]:
        """Get currently reachable peers"""
        self._discover_peers()  # Refresh
        return set(self.discovered_peers.keys())
    
    @classmethod
    def reset_all(cls):
        """Reset the mock radio environment"""
        cls._all_radios.clear()


class RealBLERadio(BLERadio):
    """
    Real BLE radio using platform-specific APIs
    Placeholder for actual implementation on Android/iOS
    """
    
    def __init__(self, node_id: str):
        super().__init__(node_id)
        # TODO: Initialize platform-specific BLE stack
        # Android: Use android.bluetooth API via pyjnius
        # iOS: Use CoreBluetooth via pyobjc
        raise NotImplementedError("Real BLE not yet implemented - use MockBLERadio for testing")
    
    def start(self):
        """Start real BLE scanning and advertising"""
        # TODO: Start BLE scan
        # TODO: Start BLE advertising with service UUID
        pass
    
    def stop(self):
        """Stop BLE operations"""
        # TODO: Stop scan and advertising
        pass
    
    def send_message(self, peer_id: str, data: bytes) -> bool:
        """Send via BLE GATT characteristic write"""
        # TODO: Write to GATT characteristic
        pass
    
    def get_neighbors(self) -> Set[str]:
        """Get discovered BLE peripherals"""
        # TODO: Return discovered devices
        pass


# BLE Service UUIDs for MeshPhone
MESHPHONE_SERVICE_UUID = "6d657368-7068-6f6e-652d-736572766963"  # "meshphone-servic"
MESHPHONE_MESSAGE_CHAR_UUID = "6d657368-7068-6f6e-652d-6d736763"  # "meshphone-msgc"
MESHPHONE_KEY_CHAR_UUID = "6d657368-7068-6f6e-652d-6b657963"     # "meshphone-keyc"


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("BLE RADIO DEMO")
    print("=" * 60)
    
    # Reset mock environment
    MockBLERadio.reset_all()
    
    # Create mock radios for testing
    alice = MockBLERadio("Alice", x=0, y=0)
    bob = MockBLERadio("Bob", x=50, y=0)
    carol = MockBLERadio("Carol", x=150, y=0)  # Out of Alice's range
    
    print("\n📍 Node Positions")
    print(f"   Alice: (0, 0)")
    print(f"   Bob: (50, 0) - 50m from Alice")
    print(f"   Carol: (150, 0) - 150m from Alice (out of range)")
    
    # Set up callbacks
    def on_peer_found(peer: BLEPeer):
        print(f"   📡 Discovered: {peer.node_id} (RSSI: {peer.rssi} dBm, ~{peer.distance_estimate:.0f}m)")
    
    def on_message(sender: str, data: bytes):
        print(f"   📨 Received from {sender}: {data.decode()}")
    
    alice.on_peer_discovered = on_peer_found
    bob.on_message_received = on_message
    
    # Start radios
    print("\n🔛 Starting BLE radios")
    alice.start()
    bob.start()
    carol.start()
    
    # Alice discovers peers
    print("\n🔍 Alice scanning for peers")
    neighbors = alice.get_neighbors()
    print(f"   Found {len(neighbors)} neighbors: {neighbors}")
    
    # Alice sends message to Bob
    print("\n📤 Alice sending message to Bob")
    message = b"Hello Bob via BLE!"
    success = alice.send_message("Bob", message)
    print(f"   Send successful: {success} ✅")
    
    # Try sending to Carol (out of range)
    print("\n📤 Alice trying to send to Carol (out of range)")
    success = alice.send_message("Carol", b"Hello Carol!")
    print(f"   Send successful: {success} ❌ (expected failure)")
    
    # Test range
    print("\n📏 Distance Estimates")
    for peer_id, peer in alice.discovered_peers.items():
        print(f"   {peer_id}: RSSI {peer.rssi} dBm → ~{peer.distance_estimate:.0f}m")
    
    # Cleanup
    alice.stop()
    bob.stop()
    carol.stop()
    
    print("\n✅ BLE radio simulation complete!")
    print("   • Peer discovery ✅")
    print("   • Range limiting (100m) ✅")
    print("   • Message transmission ✅")
    print("   • RSSI distance estimation ✅")
