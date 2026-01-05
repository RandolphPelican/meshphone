"""
Message Module - Core message structure and handling
Defines how messages are structured, encrypted, and routed through mesh
"""

import time
import uuid
import hashlib
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json


class MessageType(Enum):
    """Types of messages in the mesh network"""
    TEXT = "text"
    VOICE = "voice"
    FILE = "file"
    ACK = "ack"
    ROUTE_REQUEST = "route_request"
    ROUTE_REPLY = "route_reply"
    ROUTE_ERROR = "route_error"
    HEARTBEAT = "heartbeat"


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class MessageHeader:
    """
    Message header - readable by all nodes for routing
    Not encrypted (needed for relay decisions)
    """
    message_id: str
    sender_id: str
    recipient_id: str
    timestamp: float
    message_type: MessageType
    priority: MessagePriority = MessagePriority.NORMAL
    ttl: int = 10  # Time to live (max hops)
    sequence_number: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "timestamp": self.timestamp,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "ttl": self.ttl,
            "sequence_number": self.sequence_number,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MessageHeader':
        return cls(
            message_id=data["message_id"],
            sender_id=data["sender_id"],
            recipient_id=data["recipient_id"],
            timestamp=data["timestamp"],
            message_type=MessageType(data["message_type"]),
            priority=MessagePriority(data["priority"]),
            ttl=data["ttl"],
            sequence_number=data["sequence_number"],
        )


@dataclass
class MessagePayload:
    """
    Message payload - encrypted end-to-end
    Only sender and recipient can read this
    """
    content: str
    content_type: str = "text/plain"  # MIME type
    metadata: Dict[str, Any] = field(default_factory=dict)
    attachments: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "content_type": self.content_type,
            "metadata": self.metadata,
            "attachments": self.attachments,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MessagePayload':
        return cls(
            content=data["content"],
            content_type=data.get("content_type", "text/plain"),
            metadata=data.get("metadata", {}),
            attachments=data.get("attachments", []),
        )
    
    def get_size_bytes(self) -> int:
        """Estimate payload size in bytes"""
        return len(json.dumps(self.to_dict()).encode('utf-8'))


@dataclass
class OnionLayer:
    """
    Single layer of onion routing
    Each relay peels one layer to discover next hop
    """
    next_hop: str
    layer_encrypted: bool = False
    layer_data: Optional[bytes] = None
    
    def to_dict(self) -> Dict:
        return {
            "next_hop": self.next_hop,
            "layer_encrypted": self.layer_encrypted,
            "layer_data": self.layer_data.hex() if self.layer_data else None,
        }


@dataclass
class Message:
    """
    Complete mesh message with routing and encryption
    """
    header: MessageHeader
    payload: MessagePayload
    onion_layers: List[OnionLayer] = field(default_factory=list)
    hops_taken: List[str] = field(default_factory=list)
    energy_cost: float = 0.0
    is_encrypted: bool = False
    signature: Optional[str] = None
    
    @classmethod
    def create_text_message(cls, sender_id: str, recipient_id: str, 
                           text: str, priority: MessagePriority = MessagePriority.NORMAL) -> 'Message':
        """Factory method to create a text message"""
        message_id = str(uuid.uuid4())
        
        header = MessageHeader(
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            timestamp=time.time(),
            message_type=MessageType.TEXT,
            priority=priority,
        )
        
        payload = MessagePayload(
            content=text,
            content_type="text/plain",
        )
        
        return cls(header=header, payload=payload)
    
    @classmethod
    def create_ack(cls, original_message_id: str, sender_id: str, 
                   recipient_id: str) -> 'Message':
        """Create acknowledgment message"""
        header = MessageHeader(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            recipient_id=recipient_id,
            timestamp=time.time(),
            message_type=MessageType.ACK,
            priority=MessagePriority.HIGH,
            ttl=5,  # ACKs don't need to travel far
        )
        
        payload = MessagePayload(
            content=original_message_id,
            content_type="application/json",
            metadata={"ack_for": original_message_id}
        )
        
        return cls(header=header, payload=payload)
    
    def add_hop(self, node_id: str):
        """Record that message passed through a node"""
        self.hops_taken.append(node_id)
        self.header.ttl -= 1
    
    def is_expired(self) -> bool:
        """Check if message TTL expired"""
        return self.header.ttl <= 0
    
    def should_relay(self, current_node_id: str) -> bool:
        """Determine if current node should relay this message"""
        # Don't relay if expired
        if self.is_expired():
            return False
        
        # Don't relay if we're the recipient
        if self.header.recipient_id == current_node_id:
            return False
        
        # Don't relay if we already relayed this message (loop detection)
        if current_node_id in self.hops_taken:
            return False
        
        return True
    
    def calculate_energy_cost(self) -> float:
        """
        Calculate energy cost for this message
        Based on: payload size, hops, priority
        """
        base_cost = 100.0  # Base energy units
        
        # Size factor (larger messages cost more)
        size_kb = self.payload.get_size_bytes() / 1024
        size_factor = 1.0 + (size_kb * 0.1)  # +10% per KB
        
        # Priority factor (urgent costs more)
        priority_factors = {
            MessagePriority.LOW: 0.5,
            MessagePriority.NORMAL: 1.0,
            MessagePriority.HIGH: 1.5,
            MessagePriority.URGENT: 2.0,
        }
        priority_factor = priority_factors[self.header.priority]
        
        # Hop factor (more hops = more cost)
        expected_hops = 10 - self.header.ttl
        hop_factor = 1.0 + (expected_hops * 0.2)  # +20% per hop
        
        total_cost = base_cost * size_factor * priority_factor * hop_factor
        return round(total_cost, 2)
    
    def get_relay_reward(self) -> float:
        """Calculate reward for relaying this message"""
        # Relays get 10% of sender's cost
        return round(self.calculate_energy_cost() * 0.1, 2)
    
    def to_wire_format(self) -> bytes:
        """
        Serialize message for transmission over radio
        Returns bytes that can be sent via Bluetooth/WiFi
        """
        message_dict = {
            "header": self.header.to_dict(),
            "payload": self.payload.to_dict(),
            "hops_taken": self.hops_taken,
            "energy_cost": self.energy_cost,
            "is_encrypted": self.is_encrypted,
            "signature": self.signature,
        }
        
        return json.dumps(message_dict).encode('utf-8')
    
    @classmethod
    def from_wire_format(cls, data: bytes) -> 'Message':
        """Deserialize message from wire format"""
        message_dict = json.loads(data.decode('utf-8'))
        
        header = MessageHeader.from_dict(message_dict["header"])
        payload = MessagePayload.from_dict(message_dict["payload"])
        
        return cls(
            header=header,
            payload=payload,
            hops_taken=message_dict.get("hops_taken", []),
            energy_cost=message_dict.get("energy_cost", 0.0),
            is_encrypted=message_dict.get("is_encrypted", False),
            signature=message_dict.get("signature"),
        )
    
    def get_checksum(self) -> str:
        """Generate checksum for message integrity"""
        wire_data = self.to_wire_format()
        return hashlib.sha256(wire_data).hexdigest()[:16]
    
    def __str__(self) -> str:
        return (f"Message({self.header.message_id[:8]}... "
                f"from {self.header.sender_id} to {self.header.recipient_id}, "
                f"type={self.header.message_type.value}, "
                f"hops={len(self.hops_taken)}/{10-self.header.ttl})")


# Message queue for handling incoming/
