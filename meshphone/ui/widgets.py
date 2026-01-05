"""
Custom UI Widgets for MeshPhone
Reusable components for chat, contacts, settings
"""

from dataclasses import dataclass
from typing import Optional, Callable
from datetime import datetime


@dataclass
class MessageBubble:
    """A chat message bubble"""
    message_id: str
    sender_id: str
    content: str
    timestamp: float
    is_outgoing: bool
    is_delivered: bool = False
    is_encrypted: bool = True
    
    @property
    def time_str(self) -> str:
        """Format timestamp as HH:MM"""
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%H:%M")
    
    @property
    def date_str(self) -> str:
        """Format date"""
        dt = datetime.fromtimestamp(self.timestamp)
        today = datetime.now().date()
        msg_date = dt.date()
        
        if msg_date == today:
            return "Today"
        elif (today - msg_date).days == 1:
            return "Yesterday"
        else:
            return dt.strftime("%b %d, %Y")
    
    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "content": self.content,
            "timestamp": self.timestamp,
            "is_outgoing": self.is_outgoing,
            "is_delivered": self.is_delivered,
            "is_encrypted": self.is_encrypted,
        }


@dataclass
class ContactCard:
    """A contact in the address book"""
    node_id: str
    display_name: str
    public_key: Optional[bytes] = None
    last_seen: Optional[float] = None
    is_online: bool = False
    unread_count: int = 0
    
    @property
    def status_text(self) -> str:
        if self.is_online:
            return "Online via mesh"
        elif self.last_seen:
            dt = datetime.fromtimestamp(self.last_seen)
            return f"Last seen {dt.strftime('%b %d at %H:%M')}"
        else:
            return "Never seen"
    
    @property
    def initials(self) -> str:
        """Get initials for avatar"""
        words = self.display_name.split()
        if len(words) >= 2:
            return f"{words[0][0]}{words[1][0]}".upper()
        elif len(words) == 1 and len(words[0]) >= 2:
            return words[0][:2].upper()
        else:
            return self.node_id[:2].upper()


@dataclass
class NetworkStatusWidget:
    """Shows current network status"""
    mode: str  # "mesh", "carrier", "offline"
    mesh_neighbors: int = 0
    signal_strength: int = 0
    energy_balance: float = 1000.0
    
    @property
    def status_color(self) -> str:
        """Color code for status"""
        if self.mode == "mesh":
            return "#00ff00"  # Green
        elif self.mode == "carrier":
            return "#ffaa00"  # Orange
        else:
            return "#ff0000"  # Red
    
    @property
    def status_text(self) -> str:
        if self.mode == "mesh":
            return f"Free Mode • {self.mesh_neighbors} neighbors"
        elif self.mode == "carrier":
            return "Carrier Fallback • Using data"
        else:
            return "Offline • No connection"
    
    @property
    def energy_color(self) -> str:
        """Color based on energy level"""
        if self.energy_balance >= 500:
            return "#00ff00"
        elif self.energy_balance >= 200:
            return "#ffaa00"
        else:
            return "#ff0000"


@dataclass
class SettingToggle:
    """A settings toggle switch"""
    key: str
    label: str
    description: str
    value: bool
    on_change: Optional[Callable[[bool], None]] = None
    
    def toggle(self):
        """Toggle the value"""
        self.value = not self.value
        if self.on_change:
            self.on_change(self.value)


class MockUI:
    """
    Mock UI for testing without Kivy
    Simulates user interactions in console
    """
    
    def __init__(self):
        self.messages: list[MessageBubble] = []
        self.contacts: list[ContactCard] = []
        self.status = NetworkStatusWidget(mode="offline")
        
    def show_message(self, bubble: MessageBubble):
        """Display a message"""
        self.messages.append(bubble)
        icon = "📤" if bubble.is_outgoing else "📥"
        lock = "🔒" if bubble.is_encrypted else "🔓"
        print(f"{icon} {lock} [{bubble.time_str}] {bubble.sender_id}: {bubble.content}")
    
    def show_contact(self, contact: ContactCard):
        """Display a contact"""
        self.contacts.append(contact)
        status_icon = "🟢" if contact.is_online else "⚫"
        print(f"{status_icon} {contact.display_name} ({contact.node_id})")
        print(f"   {contact.status_text}")
        if contact.unread_count > 0:
            print(f"   💬 {contact.unread_count} unread")
    
    def update_status(self, status: NetworkStatusWidget):
        """Update network status"""
        self.status = status
        print(f"\n📶 Status: {status.status_text}")
        print(f"   Energy: {status.energy_balance:.0f}j")
    
    def show_chat_history(self, contact_id: str):
        """Show chat with a contact"""
        print(f"\n💬 Chat with {contact_id}")
        print("=" * 50)
        
        contact_messages = [m for m in self.messages if m.sender_id == contact_id or 
                          (m.is_outgoing and contact_id in str(m.message_id))]
        
        current_date = None
        for msg in sorted(contact_messages, key=lambda m: m.timestamp):
            if msg.date_str != current_date:
                print(f"\n--- {msg.date_str} ---")
                current_date = msg.date_str
            
            self.show_message(msg)
    
    def show_contacts_list(self):
        """Show all contacts"""
        print("\n📇 Contacts")
        print("=" * 50)
        
        # Sort by online status, then unread count
        sorted_contacts = sorted(
            self.contacts,
            key=lambda c: (not c.is_online, -c.unread_count, c.display_name)
        )
        
        for contact in sorted_contacts:
            self.show_contact(contact)
            print()
    
    def show_settings(self, settings: list[SettingToggle]):
        """Show settings menu"""
        print("\n⚙️  Settings")
        print("=" * 50)
        
        for i, setting in enumerate(settings, 1):
            status = "ON" if setting.value else "OFF"
            print(f"{i}. {setting.label}: {status}")
            print(f"   {setting.description}")
            print()


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("UI WIDGETS DEMO")
    print("=" * 60)
    
    ui = MockUI()
    
    # Create contacts
    alice = ContactCard(
        node_id="alice_001",
        display_name="Alice Smith",
        is_online=True,
        unread_count=0
    )
    
    bob = ContactCard(
        node_id="bob_002",
        display_name="Bob Johnson",
        is_online=False,
        last_seen=datetime.now().timestamp() - 3600,
        unread_count=2
    )
    
    # Show contacts
    print("\n📇 CONTACTS LIST")
    ui.show_contact(alice)
    print()
    ui.show_contact(bob)
    
    # Network status
    print("\n📶 NETWORK STATUS")
    status = NetworkStatusWidget(
        mode="mesh",
        mesh_neighbors=5,
        energy_balance=850.0
    )
    ui.update_status(status)
    
    # Messages
    print("\n💬 MESSAGES")
    
    msg1 = MessageBubble(
        message_id="msg_1",
        sender_id="alice_001",
        content="Hey! Just switched to Free Mode!",
        timestamp=datetime.now().timestamp(),
        is_outgoing=False,
        is_delivered=True
    )
    
    msg2 = MessageBubble(
        message_id="msg_2",
        sender_id="you",
        content="Nice! How's the mesh coverage?",
        timestamp=datetime.now().timestamp(),
        is_outgoing=True,
        is_delivered=True
    )
    
    ui.show_message(msg1)
    ui.show_message(msg2)
    
    # Settings
    print("\n⚙️  SETTINGS")
    
    settings = [
        SettingToggle(
            key="free_mode",
            label="Free Mode",
            description="Use mesh network instead of carrier",
            value=True
        ),
        SettingToggle(
            key="relay_enabled",
            label="Relay Messages",
            description="Help extend the mesh network (earns credits)",
            value=True
        ),
        SettingToggle(
            key="wifi_enabled",
            label="WiFi Direct",
            description="Use WiFi for longer range (200m)",
            value=True
        ),
        SettingToggle(
            key="lora_enabled",
            label="LoRa Module",
            description="Long-range rural coverage (requires hardware)",
            value=False
        ),
    ]
    
    ui.show_settings(settings)
    
    print("\n✅ UI widgets demo complete!")
