"""
Settings UI - Configuration and Free Mode toggle
"""

from typing import Callable, Optional, List
from dataclasses import dataclass


@dataclass
class Setting:
    """A single setting option"""
    key: str
    label: str
    description: str
    value: bool
    category: str  # "network", "privacy", "advanced"
    requires_restart: bool = False
    on_change: Optional[Callable[[bool], None]] = None
    
    def toggle(self):
        """Toggle the setting value"""
        self.value = not self.value
        if self.on_change:
            self.on_change(self.value)


@dataclass
class NetworkStats:
    """Network statistics for display"""
    mesh_neighbors: int = 0
    messages_sent: int = 0
    messages_relayed: int = 0
    messages_received: int = 0
    energy_balance: float = 1000.0
    total_earned: float = 0.0
    total_spent: float = 0.0
    carrier_cost: float = 0.0
    carrier_savings: float = 100.0  # vs monthly carrier bill


class MockSettingsUI:
    """
    Mock settings UI for testing
    Console-based settings screen
    """
    
    def __init__(self):
        self.settings: List[Setting] = []
        self.stats = NetworkStats()
        self._init_default_settings()
    
    def _init_default_settings(self):
        """Initialize default settings"""
        self.settings = [
            # Network settings
            Setting(
                key="free_mode",
                label="Free Mode",
                description="Use mesh network instead of carrier (saves $100/month)",
                value=True,
                category="network",
                requires_restart=False
            ),
            Setting(
                key="relay_enabled",
                label="Relay Messages",
                description="Help extend the mesh network and earn energy credits",
                value=True,
                category="network",
                requires_restart=False
            ),
            Setting(
                key="wifi_enabled",
                label="WiFi Direct",
                description="Use WiFi for longer range (200m vs 100m BLE)",
                value=True,
                category="network",
                requires_restart=False
            ),
            Setting(
                key="ble_enabled",
                label="Bluetooth LE",
                description="Use Bluetooth for peer discovery (100m range)",
                value=True,
                category="network",
                requires_restart=False
            ),
            Setting(
                key="lora_enabled",
                label="LoRa Module",
                description="Long-range rural coverage (requires hardware module)",
                value=False,
                category="network",
                requires_restart=True
            ),
            Setting(
                key="carrier_fallback",
                label="Carrier Fallback",
                description="Use cellular when mesh unavailable (costs money)",
                value=True,
                category="network",
                requires_restart=False
            ),
            
            # Privacy settings
            Setting(
                key="onion_routing",
                label="Onion Routing",
                description="Hide your route from relays (Tor-style privacy)",
                value=True,
                category="privacy",
                requires_restart=False
            ),
            Setting(
                key="auto_delete",
                label="Auto-Delete Messages",
                description="Delete messages after 30 days",
                value=False,
                category="privacy",
                requires_restart=False
            ),
            
            # Advanced settings
            Setting(
                key="developer_mode",
                label="Developer Mode",
                description="Show technical details and debug info",
                value=False,
                category="advanced",
                requires_restart=True
            ),
        ]
    
    def get_setting(self, key: str) -> Optional[Setting]:
        """Get a setting by key"""
        return next((s for s in self.settings if s.key == key), None)
    
    def update_stats(self, stats: NetworkStats):
        """Update network statistics"""
        self.stats = stats
    
    def show_settings(self):
        """Display settings screen"""
        print("\n" + "=" * 60)
        print("⚙️  MESHPHONE SETTINGS")
        print("=" * 60)
        
        # Group by category
        categories = {
            "network": "📶 Network",
            "privacy": "🔒 Privacy",
            "advanced": "🔧 Advanced"
        }
        
        for cat_key, cat_label in categories.items():
            print(f"\n{cat_label}")
            print("-" * 60)
            
            cat_settings = [s for s in self.settings if s.category == cat_key]
            
            for setting in cat_settings:
                status = "ON " if setting.value else "OFF"
                indicator = "●" if setting.value else "○"
                restart = " (restart required)" if setting.requires_restart else ""
                
                print(f"\n{indicator} {setting.label}: {status}{restart}")
                print(f"   {setting.description}")
    
    def show_stats(self):
        """Display network statistics"""
        print("\n" + "=" * 60)
        print("📊 NETWORK STATISTICS")
        print("=" * 60)
        
        print(f"\n🌐 Mesh Network")
        print(f"   Neighbors: {self.stats.mesh_neighbors}")
        print(f"   Messages sent: {self.stats.messages_sent}")
        print(f"   Messages relayed: {self.stats.messages_relayed}")
        print(f"   Messages received: {self.stats.messages_received}")
        
        print(f"\n⚡ Energy")
        print(f"   Balance: {self.stats.energy_balance:.0f}j")
        print(f"   Total earned: {self.stats.total_earned:.0f}j (from relaying)")
        print(f"   Total spent: {self.stats.total_spent:.0f}j (from sending)")
        print(f"   Net: {self.stats.total_earned - self.stats.total_spent:+.0f}j")
        
        print(f"\n💰 Cost Savings")
        print(f"   Carrier cost this month: ${self.stats.carrier_cost:.2f}")
        print(f"   vs AT&T bill: $100.00")
        print(f"   Savings: ${self.stats.carrier_savings:.2f}")
        print(f"   Annual savings: ${self.stats.carrier_savings * 12:.2f}")
    
    def show_about(self):
        """Display about screen"""
        print("\n" + "=" * 60)
        print("ℹ️  ABOUT MESHPHONE")
        print("=" * 60)
        
        print("""
MeshPhone - Free Encrypted Mesh Network

Version: 0.1.0 (Alpha)
License: GPL-3.0

What is MeshPhone?
------------------
MeshPhone creates a free, encrypted peer-to-peer phone network
that runs on existing devices. No monthly bills. No surveillance.
No carrier monopolies.

How it works:
- Your phone becomes a mesh network node
- Messages hop from phone to phone using Bluetooth/WiFi
- End-to-end encrypted (Signal Protocol)
- Onion routing for privacy (Tor-style)
- Energy credits reward relayers

Technology:
- Routing: AODV (Ad-hoc On-Demand Distance Vector)
- Encryption: X25519 + Signal Protocol
- Radio: BLE (100m), WiFi Direct (200m), LoRa (8km+)
- Energy: Credit-based economic incentives

Created by: John Stabler
GitHub: https://github.com/RandolphPelican/meshphone
Support: meshphone@example.com

"Free the network. Own your communication."
        """)
    
    def toggle_setting(self, key: str):
        """Toggle a setting on/off"""
        setting = self.get_setting(key)
        if setting:
            setting.toggle()
            print(f"\n✓ {setting.label} {'enabled' if setting.value else 'disabled'}")
            
            if setting.requires_restart:
                print("⚠️  Restart required for this change to take effect")


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("SETTINGS UI DEMO")
    print("=" * 60)
    
    # Create settings UI
    ui = MockSettingsUI()
    
    # Show settings
    ui.show_settings()
    
    # Show stats
    stats = NetworkStats(
        mesh_neighbors=12,
        messages_sent=47,
        messages_relayed=23,
        messages_received=51,
        energy_balance=1150.0,
        total_earned=250.0,
        total_spent=100.0,
        carrier_cost=0.50,
        carrier_savings=99.50
    )
    ui.update_stats(stats)
    ui.show_stats()
    
    # Show about
    ui.show_about()
    
    # Toggle a setting
    print("\n" + "=" * 60)
    print("TESTING TOGGLE")
    print("=" * 60)
    ui.toggle_setting("free_mode")
    ui.toggle_setting("lora_enabled")
    
    print("\n✅ Settings UI demo complete!")
    print("   • Settings categories ✅")
    print("   • Network stats ✅")
    print("   • About screen ✅")
    print("   • Toggle functionality ✅")
