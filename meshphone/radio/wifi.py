"""
WiFi Direct/Aware Radio Layer
Handles longer-range mesh connections (200-500m)
"""

import time
import socket
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum


class WiFiMode(Enum):
    """WiFi operating modes"""
    OFF = "off"
    DIRECT = "direct"  # WiFi Direct (P2P)
    AWARE = "aware"    # WiFi Aware (Neighbor Awareness Networking)


@dataclass
class WiFiPeer:
    """A discovered WiFi peer"""
    node_id: str
    ip_address: str
    port: int
    rssi: int
    last_seen: float
    public_key: Optional[bytes] = None
    mode: WiFiMode = WiFiMode.DIRECT
    
    @property
    def distance_estimate(self) -> float:
        """Estimate distance from RSSI (WiFi has better range than BLE)"""
        if self.rssi >= -50:
            return 10.0
        elif self.rssi >= -70:
            return 100.0
        elif self.rssi >= -85:
            return 300.0
        else:
            return 500.0
    
    @property
    def is_stale(self, timeout: float = 60.0) -> bool:
        """WiFi peers can be stale if not seen for 60s"""
        return (time.time() - self.last_seen) > timeout


class WiFiRadio(ABC):
    """
    Abstract WiFi radio interface
    Supports both WiFi Direct and WiFi Aware
    """
    
    def __init__(self, node_id: str, port: int = 8888):
        self.node_id = node_id
        self.port = port
        self.mode = WiFiMode.OFF
        self.discovered_peers: Dict[str, WiFiPeer] = {}
        self.on_peer_discovered: Optional[Callable[[WiFiPeer], None]] = None
        self.on_message_received: Optional[Callable[[str, bytes], None]] = None
        
    @abstractmethod
    def start(self, mode: WiFiMode = WiFiMode.DIRECT):
        """Start WiFi radio in specified mode"""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop WiFi radio"""
        pass
    
    @abstractmethod
    def send_message(self, peer_id: str, data: bytes) -> bool:
        """Send message to peer via WiFi"""
        pass
    
    @abstractmethod
    def get_neighbors(self) -> Set[str]:
        """Get currently reachable peers"""
        pass
    
    def cleanup_stale_peers(self, timeout: float = 60.0):
        """Remove stale peers"""
        stale = [
            pid for pid, peer in self.discovered_peers.items()
            if peer.is_stale(timeout)
        ]
        for pid in stale:
            del self.discovered_peers[pid]


class MockWiFiRadio(WiFiRadio):
    """
    Mock WiFi radio for testing
    Simulates WiFi Direct with longer range than BLE
    """
    
    _all_radios: Dict[str, 'MockWiFiRadio'] = {}
    
    def __init__(self, node_id: str, x: float = 0.0, y: float = 0.0,
                 max_range: float = 200.0, port: int = 8888):
        super().__init__(node_id, port)
        self.x = x
        self.y = y
        self.max_range = max_range
        self.public_key = f"wifi_key_{node_id}".encode()
        
        MockWiFiRadio._all_radios[node_id] = self
    
    def distance_to(self, other: 'MockWiFiRadio') -> float:
        """Calculate distance to another radio"""
        return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5
    
    def start(self, mode: WiFiMode = WiFiMode.DIRECT):
        """Start WiFi Direct"""
        self.mode = mode
        self._discover_peers()
    
    def stop(self):
        """Stop WiFi"""
        self.mode = WiFiMode.OFF
        self.discovered_peers.clear()
    
    def _discover_peers(self):
        """Discover WiFi peers in range"""
        for peer_id, peer_radio in MockWiFiRadio._all_radios.items():
            if peer_id == self.node_id:
                continue
            
            if peer_radio.mode == WiFiMode.OFF:
                continue
            
            distance = self.distance_to(peer_radio)
            
            if distance <= self.max_range:
                # WiFi RSSI: better than BLE at same distance
                rssi = int(-30 - (15 * (distance / 10)))
                
                peer = WiFiPeer(
                    node_id=peer_id,
                    ip_address=f"192.168.49.{hash(peer_id) % 254 + 1}",
                    port=peer_radio.port,
                    rssi=rssi,
                    last_seen=time.time(),
                    public_key=peer_radio.public_key,
                    mode=self.mode
                )
                
                self.discovered_peers[peer_id] = peer
                
                if self.on_peer_discovered:
                    self.on_peer_discovered(peer)
    
    def send_message(self, peer_id: str, data: bytes) -> bool:
        """Send via WiFi Direct"""
        if peer_id not in self.discovered_peers:
            return False
        
        peer_radio = MockWiFiRadio._all_radios.get(peer_id)
        if not peer_radio:
            return False
        
        # Simulate WiFi packet transmission
        if peer_radio.on_message_received:
            peer_radio.on_message_received(self.node_id, data)
        
        return True
    
    def get_neighbors(self) -> Set[str]:
        """Get WiFi neighbors"""
        self._discover_peers()
        return set(self.discovered_peers.keys())
    
    @classmethod
    def reset_all(cls):
        """Reset mock environment"""
        cls._all_radios.clear()


class RealWiFiRadio(WiFiRadio):
    """
    Real WiFi Direct/Aware implementation
    Platform-specific via Android WiFi P2P API or iOS Multipeer Connectivity
    """
    
    def __init__(self, node_id: str, port: int = 8888):
        super().__init__(node_id, port)
        raise NotImplementedError("Real WiFi not yet implemented - use MockWiFiRadio")
    
    def start(self, mode: WiFiMode = WiFiMode.DIRECT):
        """
        Android: Use WifiP2pManager for WiFi Direct
        iOS: Use MultipeerConnectivity framework
        """
        pass
    
    def stop(self):
        pass
    
    def send_message(self, peer_id: str, data: bytes) -> bool:
        """Send via WiFi Direct socket"""
        pass
    
    def get_neighbors(self) -> Set[str]:
        pass


class HybridRadio:
    """
    Combines BLE and WiFi for optimal performance
    Uses BLE for discovery, WiFi for data transfer
    """
    
    def __init__(self, ble_radio, wifi_radio):
        self.ble = ble_radio
        self.wifi = wifi_radio
        self.node_id = ble_radio.node_id
        
    def start(self):
        """Start both radios"""
        self.ble.start()
        self.wifi.start(WiFiMode.DIRECT)
    
    def stop(self):
        """Stop both radios"""
        self.ble.stop()
        self.wifi.stop()
    
    def get_neighbors(self) -> Set[str]:
        """Get neighbors from both radios"""
        ble_neighbors = self.ble.get_neighbors()
        wifi_neighbors = self.wifi.get_neighbors()
        return ble_neighbors | wifi_neighbors  # Union
    
    def send_message(self, peer_id: str, data: bytes) -> bool:
        """
        Smart routing: Use WiFi if available (faster), fallback to BLE
        """
        # Try WiFi first (faster, longer range)
        if peer_id in self.wifi.discovered_peers:
            if self.wifi.send_message(peer_id, data):
                return True
        
        # Fallback to BLE
        if peer_id in self.ble.discovered_peers:
            return self.ble.send_message(peer_id, data)
        
        return False


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("WIFI RADIO DEMO")
    print("=" * 60)
    
    MockWiFiRadio.reset_all()
    
    # Create radios with longer range than BLE
    alice = MockWiFiRadio("Alice", x=0, y=0, max_range=200)
    bob = MockWiFiRadio("Bob", x=150, y=0, max_range=200)
    carol = MockWiFiRadio("Carol", x=300, y=0, max_range=200)  # Out of Alice's range
    
    print("\n📍 Node Positions")
    print(f"   Alice: (0, 0)")
    print(f"   Bob: (150, 0) - 150m from Alice")
    print(f"   Carol: (300, 0) - 300m from Alice (out of range)")
    
    # Callbacks
    def on_peer(peer: WiFiPeer):
        print(f"   📡 Discovered: {peer.node_id} at {peer.ip_address} (RSSI: {peer.rssi} dBm)")
    
    def on_msg(sender: str, data: bytes):
        print(f"   📨 Received from {sender}: {data.decode()}")
    
    alice.on_peer_discovered = on_peer
    bob.on_message_received = on_msg
    
    # Start WiFi
    print("\n🔛 Starting WiFi Direct")
    alice.start(WiFiMode.DIRECT)
    bob.start(WiFiMode.DIRECT)
    carol.start(WiFiMode.DIRECT)
    
    # Alice discovers
    print("\n🔍 Alice scanning for WiFi peers")
    neighbors = alice.get_neighbors()
    print(f"   Found {len(neighbors)} neighbors: {neighbors}")
    
    # Send message
    print("\n📤 Alice → Bob (WiFi)")
    success = alice.send_message("Bob", b"Hello via WiFi Direct!")
    print(f"   Success: {success} ✅")
    
    # Out of range
    print("\n📤 Alice → Carol (out of range)")
    success = alice.send_message("Carol", b"Hello Carol!")
    print(f"   Success: {success} ❌")
    
    # Compare ranges
    print("\n📏 WiFi vs BLE Range")
    print(f"   BLE: ~100m")
    print(f"   WiFi: ~200m (2x better)")
    print(f"   Bob at 150m: Reachable via WiFi, not BLE ✅")
    
    alice.stop()
    bob.stop()
    carol.stop()
    
    print("\n✅ WiFi radio simulation complete!")
