"""
Chat UI - Main messaging interface
Built with Kivy for cross-platform mobile support
"""

from typing import List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChatMessage:
    """Represents a message in the chat UI"""
    message_id: str
    sender_name: str
    content: str
    timestamp: float
    is_outgoing: bool
    is_delivered: bool = True
    
    @property
    def time_str(self) -> str:
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%H:%M")
    
    @property
    def bubble_color(self) -> tuple:
        """Color for message bubble"""
        if self.is_outgoing:
            return (0.2, 0.6, 1.0, 1.0)  # Blue for sent
        else:
            return (0.9, 0.9, 0.9, 1.0)  # Gray for received
    
    @property
    def text_color(self) -> tuple:
        """Color for message text"""
        if self.is_outgoing:
            return (1.0, 1.0, 1.0, 1.0)  # White for sent
        else:
            return (0.0, 0.0, 0.0, 1.0)  # Black for received


@dataclass
class ChatContact:
    """Contact in the chat list"""
    node_id: str
    display_name: str
    last_message: str = ""
    last_message_time: float = 0
    unread_count: int = 0
    is_online: bool = False
    
    @property
    def status_icon(self) -> str:
        return "●" if self.is_online else "○"
    
    @property
    def status_color(self) -> tuple:
        if self.is_online:
            return (0.0, 1.0, 0.0, 1.0)  # Green
        else:
            return (0.5, 0.5, 0.5, 1.0)  # Gray
    
    @property
    def time_str(self) -> str:
        if self.last_message_time == 0:
            return ""
        dt = datetime.fromtimestamp(self.last_message_time)
        now = datetime.now()
        
        if dt.date() == now.date():
            return dt.strftime("%H:%M")
        else:
            return dt.strftime("%b %d")


class MockChatUI:
    """
    Mock chat UI for testing without Kivy
    Console-based interface
    """
    
    def __init__(self):
        self.contacts: List[ChatContact] = []
        self.messages: dict[str, List[ChatMessage]] = {}
        self.current_chat: Optional[str] = None
        self.on_send_message: Optional[Callable[[str, str], None]] = None
        
    def add_contact(self, contact: ChatContact):
        """Add a contact to the list"""
        self.contacts.append(contact)
        if contact.node_id not in self.messages:
            self.messages[contact.node_id] = []
    
    def add_message(self, contact_id: str, message: ChatMessage):
        """Add a message to a conversation"""
        if contact_id not in self.messages:
            self.messages[contact_id] = []
        
        self.messages[contact_id].append(message)
        
        # Update contact's last message
        for contact in self.contacts:
            if contact.node_id == contact_id:
                contact.last_message = message.content[:50]
                contact.last_message_time = message.timestamp
                if not message.is_outgoing:
                    contact.unread_count += 1
                break
    
    def show_contact_list(self):
        """Display the contact list"""
        print("\n" + "=" * 60)
        print("📱 MESHPHONE - CHATS")
        print("=" * 60)
        
        if not self.contacts:
            print("No contacts yet. Add someone to start chatting!")
            return
        
        # Sort by last message time
        sorted_contacts = sorted(
            self.contacts,
            key=lambda c: c.last_message_time,
            reverse=True
        )
        
        for i, contact in enumerate(sorted_contacts, 1):
            status = contact.status_icon
            unread = f"({contact.unread_count})" if contact.unread_count > 0 else ""
            
            print(f"\n{i}. {status} {contact.display_name} {unread}")
            if contact.last_message:
                print(f"   {contact.last_message}")
                print(f"   {contact.time_str}")
    
    def show_chat(self, contact_id: str):
        """Display a conversation"""
        self.current_chat = contact_id
        
        # Find contact
        contact = next((c for c in self.contacts if c.node_id == contact_id), None)
        if not contact:
            print(f"Contact {contact_id} not found")
            return
        
        # Mark as read
        contact.unread_count = 0
        
        print("\n" + "=" * 60)
        print(f"💬 Chat with {contact.display_name}")
        print("=" * 60)
        
        messages = self.messages.get(contact_id, [])
        
        if not messages:
            print("\nNo messages yet. Say hi!")
            return
        
        # Group messages by date
        current_date = None
        for msg in sorted(messages, key=lambda m: m.timestamp):
            msg_date = datetime.fromtimestamp(msg.timestamp).date()
            
            if msg_date != current_date:
                date_str = "Today" if msg_date == datetime.now().date() else msg_date.strftime("%b %d, %Y")
                print(f"\n--- {date_str} ---")
                current_date = msg_date
            
            # Format message
            side = "→" if msg.is_outgoing else "←"
            status = "✓" if msg.is_delivered else "○"
            
            print(f"\n{side} [{msg.time_str}] {status}")
            print(f"   {msg.content}")
    
    def send_message(self, content: str):
        """Send a message in current chat"""
        if not self.current_chat:
            print("No chat selected")
            return
        
        if self.on_send_message:
            self.on_send_message(self.current_chat, content)
        
        # Add to UI
        msg = ChatMessage(
            message_id=f"msg_{len(self.messages.get(self.current_chat, []))}",
            sender_name="You",
            content=content,
            timestamp=datetime.now().timestamp(),
            is_outgoing=True,
            is_delivered=False  # Will be marked delivered when confirmed
        )
        
        self.add_message(self.current_chat, msg)
        print(f"✓ Sent: {content}")
    
    def show_status_bar(self, mesh_neighbors: int, energy_balance: float, mode: str):
        """Show network status"""
        print("\n" + "-" * 60)
        
        if mode == "mesh":
            print(f"📶 Free Mode • {mesh_neighbors} neighbors • {energy_balance:.0f}j")
        elif mode == "carrier":
            print(f"📞 Carrier Fallback • {energy_balance:.0f}j")
        else:
            print(f"⚠️  Offline • {energy_balance:.0f}j")


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("CHAT UI DEMO")
    print("=" * 60)
    
    # Create UI
    ui = MockChatUI()
    
    # Add contacts
    alice = ChatContact(
        node_id="alice_001",
        display_name="Alice",
        last_message="Hey! Free Mode is awesome!",
        last_message_time=datetime.now().timestamp() - 3600,
        unread_count=2,
        is_online=True
    )
    
    bob = ChatContact(
        node_id="bob_002",
        display_name="Bob",
        last_message="See you at the meetup",
        last_message_time=datetime.now().timestamp() - 7200,
        unread_count=0,
        is_online=False
    )
    
    ui.add_contact(alice)
    ui.add_contact(bob)
    
    # Add some messages to Alice's chat
    msg1 = ChatMessage(
        message_id="msg_1",
        sender_name="Alice",
        content="Hey! Just switched to MeshPhone!",
        timestamp=datetime.now().timestamp() - 3700,
        is_outgoing=False
    )
    
    msg2 = ChatMessage(
        message_id="msg_2",
        sender_name="You",
        content="Nice! How's the mesh coverage?",
        timestamp=datetime.now().timestamp() - 3650,
        is_outgoing=True
    )
    
    msg3 = ChatMessage(
        message_id="msg_3",
        sender_name="Alice",
        content="Really good! I see 8 neighbors. No carrier bills! 🎉",
        timestamp=datetime.now().timestamp() - 3600,
        is_outgoing=False
    )
    
    ui.add_message("alice_001", msg1)
    ui.add_message("alice_001", msg2)
    ui.add_message("alice_001", msg3)
    
    # Show contact list
    ui.show_contact_list()
    
    # Show Alice's chat
    ui.show_chat("alice_001")
    
    # Show status
    ui.show_status_bar(
        mesh_neighbors=8,
        energy_balance=950.0,
        mode="mesh"
    )
    
    print("\n\n✅ Chat UI demo complete!")
    print("   • Contact list ✅")
    print("   • Message bubbles ✅")
    print("   • Timestamps ✅")
    print("   • Status indicators ✅")
