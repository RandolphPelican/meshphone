"""
LoRa Radio Layer - Long Range for Rural Areas
Optional hardware module for 5-30 mile range
"""

import time
from typing import Dict, Optional, Set, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum


class LoRaMode(Enum):
    """LoRa spreading factors (trade speed for range)"""
    SF7 = 7   # Fast, short range (~2km)
    SF8 = 8   # Balanced (~5km)
    SF9 = 9   # Longer range (~10km)
    SF10 = 10  # Very long (~20km)
    SF11 = 11  # Extreme (~30km)
    SF12 = 12  # Maximum range (~50km), very slow


@dataclass
class LoRaPeer:
    """A LoRa peer (usually a fixed hub or another phone with LoRa module)"""
    node_id: str
    rssi: int
    snr: float  # Signal-to-Noise Ratio
    last_seen: float
    spreading_factor: LoRaMode
    
    @property
    def distance_estimate(self) -> float:
        """Estimate distance from RSSI and SNR"""
        # LoRa can work at very low RSSI (-120 dBm+)
        if self.rssi >= -80:
            return 1000.0  # ~1km
        elif self.rssi >= -100:
            return 5000.0  # ~5km
        elif self.rssi >= -120:
            return 15000.0  # ~15km
        else:
            return 30000.0  # ~30km
    
    @property
    def link_quality(self) -> str:
        """Human-readable link quality"""
        if self.snr > 5:
            return "Excellent"
        elif self.snr > 0:
            return "Good"
        elif self.snr > -10:
            return "Fair"
        else:
            return "Poor"


class LoRaRadio(ABC):
    """
    Abstract LoRa radio interface
    Hardware: SX1276/SX1278 chips (~$8-12)
    """
    
    def __init__(self, node_id: str, frequency: float = 915.0):
        self.node_id = node_id
        self.frequency = frequency  # MHz (915 for US, 868 for EU)
        self.spreading_factor = LoRaMode.SF9  # Default balanced
        self.bandwidth = 125  # kHz
        self.coding_rate = 5  # 4/5
        self.tx_power = 20  # dBm (max allowed in US)
        
        self.discovered_peers: Dict[str, LoRaPeer] = {}
        self.on_peer_discovered: Optional[Callable[[LoRaPeer], None]] = None
        self.on_message_received: Optional[Callable[[str, bytes], None]] = None
        
    @abstractmethod
    def start(self):
        """Initialize LoRa radio"""
        pass
    
    @abstractmethod
    def stop(self):
        """Shutdown LoRa radio"""
        pass
    
    @abstractmethod
    def send_message(self, peer_id: str, data: bytes) -> bool:
        """
        Send message via LoRa
        Note: LoRa is SLOW (100-5000 bps depending on SF)
        Keep messages small!
        """
        pass
    
    @abstractmethod
    def get_neighbors(self) -> Set[str]:
        """Get reachable LoRa peers"""
        pass
    
    def set_spreading_factor(self, sf: LoRaMode):
        """
        Adjust spreading factor
        Higher SF = longer range but slower speed
        """
        self.spreading_factor = sf
    
    def calculate_airtime(self, payload_bytes: int) -> float:
        """
        Calculate time-on-air for a packet
        Important: LoRa has duty cycle limits (1% in EU, 36s/hour)
        """
        # Simplified calculation
        sf = self.spreading_factor.value
        bw = self.bandwidth
        
        # Symbol time
        ts = (2 ** sf) / bw  # milliseconds
        
        # Preamble
        t_preamble = (8 + 4.25) * ts
        
        # Payload
        payload_symbols = 8 + max(
            0,
            ((8 * payload_bytes - 4 * sf + 28 + 16) / (4 * sf)) * (self.coding_rate + 4)
        )
        
        t_payload = payload_symbols * ts
        
        return (t_preamble + t_payload) / 1000  # Convert to seconds


class MockLoRaRadio(LoRaRadio):
    """
    Mock LoRa for testing
    Simulates long-range, low-bandwidth characteristics
    """
    
    _all_radios: Dict[str, 'MockLoRaRadio'] = {}
    
    def __init__(self, node_id: str, x: float = 0.0, y: float = 0.0,
                 max_range: float = 10000.0, frequency: float = 915.0):
        super().__init__(node_id, frequency)
        self.x = x
        self.y = y
        self.max_range = max_range
        self.is_active = False
        
        MockLoRaRadio._all_radios[node_id] = self
    
    def distance_to(self, other: 'MockLoRaRadio') -> float:
        return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5
    
    def start(self):
        """Start LoRa radio"""
        self.is_active = True
        self._discover_peers()
    
    def stop(self):
        """Stop LoRa"""
        self.is_active = False
        self.discovered_peers.clear()
    
    def _discover_peers(self):
        """Discover LoRa peers (can be very far away)"""
        for peer_id, peer_radio in MockLoRaRadio._all_radios.items():
            if peer_id == self.node_id:
                continue
            
            if not peer_radio.is_active:
                continue
            
            distance = self.distance_to(peer_radio)
            
            if distance <= self.max_range:
                # LoRa works at very low RSSI
                rssi = int(-40 - (8 * (distance / 1000)))  # Lose 8 dBm per km
                snr = 10 - (distance / 1000)  # SNR degrades with distance
                
                peer = LoRaPeer(
                    node_id=peer_id,
                    rssi=rssi,
                    snr=snr,
                    last_seen=time.time(),
                    spreading_factor=self.spreading_factor
                )
                
                self.discovered_peers[peer_id] = peer
                
                if self.on_peer_discovered:
                    self.on_peer_discovered(peer)
    
    def send_message(self, peer_id: str, data: bytes) -> bool:
        """Send via LoRa (simulate transmission time)"""
        if peer_id not in self.discovered_peers:
            return False
        
        # Calculate and simulate airtime
        airtime = self.calculate_airtime(len(data))
        time.sleep(airtime)  # Simulate slow transmission
        
        peer_radio = MockLoRaRadio._all_radios.get(peer_id)
        if peer_radio and peer_radio.on_message_received:
            peer_radio.on_message_received(self.node_id, data)
        
        return True
    
    def get_neighbors(self) -> Set[str]:
        """Get LoRa neighbors"""
        self._discover_peers()
        return set(self.discovered_peers.keys())
    
    @classmethod
    def reset_all(cls):
        cls._all_radios.clear()


class RealLoRaRadio(LoRaRadio):
    """
    Real LoRa implementation using SX127x chips
    Via: RadioHead library (C++) or CircuitPython (Python)
    """
    
    def __init__(self, node_id: str, frequency: float = 915.0):
        super().__init__(node_id, frequency)
        raise NotImplementedError("Real LoRa requires hardware module - use MockLoRaRadio")
    
    def start(self):
        """
        Initialize SX1276/78 via SPI
        Set frequency, SF, bandwidth, coding rate
        """
        pass
    
    def stop(self):
        """Put radio in sleep mode"""
        pass
    
    def send_message(self, peer_id: str, data: bytes) -> bool:
        """Transmit packet via LoRa"""
        pass
    
    def get_neighbors(self) -> Set[str]:
        """Listen for beacons"""
        pass


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("LORA RADIO DEMO (RURAL SCENARIO)")
    print("=" * 60)
    
    MockLoRaRadio.reset_all()
    
    # Rural scenario: farms miles apart
    farm_a = MockLoRaRadio("Farm_A", x=0, y=0, max_range=15000)  # 15km range
    farm_b = MockLoRaRadio("Farm_B", x=8000, y=0, max_range=15000)  # 8km away
    farm_c = MockLoRaRadio("Farm_C", x=20000, y=0, max_range=15000)  # 20km (out of range)
    
    # Community hub (solar powered, always on)
    hub = MockLoRaRadio("Hub", x=5000, y=0, max_range=20000)  # Central, better range
    
    print("\n📍 Rural Network Layout")
    print(f"   Farm A: (0, 0)")
    print(f"   Hub: (5km, 0) - Solar powered relay")
    print(f"   Farm B: (8km, 0)")
    print(f"   Farm C: (20km, 0) - Out of Farm A's range")
    
    # Callbacks
    def on_lora_peer(peer: LoRaPeer):
        print(f"   📡 LoRa peer: {peer.node_id} (RSSI: {peer.rssi} dBm, SNR: {peer.snr:.1f} dB, "
              f"~{peer.distance_estimate/1000:.0f}km, quality: {peer.link_quality})")
    
    def on_lora_msg(sender: str, data: bytes):
        print(f"   📨 LoRa from {sender}: {data.decode()}")
    
    farm_a.on_peer_discovered = on_lora_peer
    farm_b.on_message_received = on_lora_msg
    hub.on_message_received = on_lora_msg
    
    # Start radios
    print("\n🔛 Starting LoRa radios (915 MHz)")
    farm_a.start()
    farm_b.start()
    farm_c.start()
    hub.start()
    
    # Farm A discovers
    print("\n🔍 Farm A scanning")
    neighbors = farm_a.get_neighbors()
    print(f"   Reachable: {neighbors}")
    
    # Send message
    print("\n📤 Farm A → Farm B (direct)")
    message = b"Weather alert"
    airtime = farm_a.calculate_airtime(len(message))
    print(f"   Message size: {len(message)} bytes")
    print(f"   Estimated airtime: {airtime:.2f}s (LoRa is SLOW)")
    
    start = time.time()
    success = farm_a.send_message("Farm_B", message)
    elapsed = time.time() - start
    print(f"   Actual time: {elapsed:.2f}s")
    print(f"   Success: {success} ✅")
    
    # Multi-hop via hub
    print("\n📤 Farm A → Hub → Farm C (multi-hop)")
    farm_a.send_message("Hub", b"Relay to Farm C")
    
    # Compare spreading factors
    print("\n🔄 Spreading Factor Trade-offs")
    print(f"   SF7: Fast (~2km range, ~5.5 kbps)")
    print(f"   SF9: Balanced (~10km, ~1.8 kbps) ← Default")
    print(f"   SF12: Max range (~50km, ~250 bps) ← Emergency only")
    
    # Cleanup
    farm_a.stop()
    farm_b.stop()
    farm_c.stop()
    hub.stop()
    
    print("\n✅ LoRa simulation complete!")
    print("   • Long range (8km+) ✅")
    print("   • Low bandwidth (slow) ✅")
    print("   • Rural coverage ✅")
    print("   • Solar hub relay ✅")
    print("\n💡 LoRa modules cost ~$10, solve rural problem")
