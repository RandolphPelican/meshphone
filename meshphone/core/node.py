"""
Node Module - Represents a phone as a mesh network node
Combines routing, energy, and message handling
"""

from typing import Dict, Set, List, Optional
from dataclasses import dataclass, field
import time

from meshphone.core.routing import Router
from meshphone.core.energy import EnergyAccount
from meshphone.core.message import Message, MessageType, MessagePriority


@dataclass
class NodeConfig:
    """Configuration for a mesh node"""
    node_id: str
    enable_relay: bool = True
    is_plugged_in: bool = False
    max_relay_queue: int = 100
    initial_energy: float = 1000.0
    ble_range: float = 100.0  # meters
    wifi_range: float = 200.0  # meters


class MeshNode:
    """
    A complete mesh network node (phone)
    Handles routing, energy, messages, and relay decisions
    """
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self.node_id = config.node_id
        
        # Core components
        self.router = Router(config.node_id)
        self.energy_account = EnergyAccount(
            node_id=config.node_id,
            balance=config.initial_energy,
            is_plugged_in=config.is_plugged_in,
        )
        
        # Network state
        self.neighbors: Set[str] = set()
        self.network_graph: Dict[str, Set[str]] = {}
        
        # Message queues
        self.outgoing_queue: List[Message] = []
        self.relay_queue: List[Message] = []
        self.received_messages: List[Message] = []
        
        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_relayed": 0,
            "messages_received": 0,
            "messages_dropped": 0,
            "relay_queue_full": 0,
        }
        
        # Seen messages (prevent loops)
        self.seen_message_ids: Set[str] = set()
        
    def update_neighbors(self, neighbors: Set[str]):
        """Update list of directly reachable neighbors"""
        self.neighbors = neighbors
        self.router.update_neighbors(neighbors)
    
    def update_network_graph(self, graph: Dict[str, Set[str]]):
        """Update view of overall network topology"""
        self.network_graph = graph
    
    def send_message(self, recipient_id: str, content: str, 
                    priority: MessagePriority = MessagePriority.NORMAL) -> Optional[Message]:
        """
        Send a message to another node
        Returns Message if successful, None if failed
        """
        # Create message
        msg = Message.create_text_message(
            sender_id=self.node_id,
            recipient_id=recipient_id,
            text=content,
            priority=priority
        )
        
        # Calculate energy cost
        energy_cost = msg.calculate_energy_cost()
        
        # Check if we can afford it
        if not self.energy_account.can_afford(energy_cost):
            print(f"❌ {self.node_id}: Insufficient energy ({self.energy_account.balance}j < {energy_cost}j)")
            return None
        
        # Find route
        route = self.router.find_route(recipient_id, self.network_graph)
        if not route:
            print(f"❌ {self.node_id}: No route to {recipient_id}")
            return None
        
        # Deduct energy
        self.energy_account.debit(energy_cost, "send", msg.header.message_id)
        msg.energy_cost = energy_cost
        
        # Add to outgoing queue
        msg.add_hop(self.node_id)
        self.outgoing_queue.append(msg)
        self.stats["messages_sent"] += 1
        
        return msg
    
    def receive_message(self, msg: Message) -> bool:
        """
        Receive a message (either for us or to relay)
        Returns True if processed, False if dropped
        """
        # Check if we've seen this message before (loop prevention)
        if msg.header.message_id in self.seen_message_ids:
            self.stats["messages_dropped"] += 1
            return False
        
        self.seen_message_ids.add(msg.header.message_id)
        
        # Check if message is for us
        if msg.header.recipient_id == self.node_id:
            self.received_messages.append(msg)
            self.stats["messages_received"] += 1
            
            # Send ACK
            ack = Message.create_ack(
                original_message_id=msg.header.message_id,
                sender_id=self.node_id,
                recipient_id=msg.header.sender_id
            )
            self.outgoing_queue.append(ack)
            
            return True
        
        # Check if we should relay
        if not self.config.enable_relay:
            self.stats["messages_dropped"] += 1
            return False
        
        if not msg.should_relay(self.node_id):
            self.stats["messages_dropped"] += 1
            return False
        
        # Check relay queue capacity
        if len(self.relay_queue) >= self.config.max_relay_queue:
            self.stats["relay_queue_full"] += 1
            self.stats["messages_dropped"] += 1
            return False
        
        # Add to relay queue
        msg.add_hop(self.node_id)
        self.relay_queue.append(msg)
        
        # Earn relay reward
        relay_reward = msg.get_relay_reward()
        self.energy_account.credit(relay_reward, "relay", from_node=msg.header.sender_id, 
                                   message_id=msg.header.message_id)
        
        self.stats["messages_relayed"] += 1
        
        return True
    
    def process_relay_queue(self) -> List[Message]:
        """
        Process relay queue and return messages ready to forward
        """
        messages_to_forward = []
        
        for msg in self.relay_queue[:]:  # Copy to allow removal during iteration
            # Find next hop
            route = self.router.find_route(msg.header.recipient_id, self.network_graph)
            
            if route and len(route) > 1:
                # Found route, ready to forward
                messages_to_forward.append(msg)
                self.relay_queue.remove(msg)
            elif msg.is_expired():
                # Message expired, drop it
                self.relay_queue.remove(msg)
                self.stats["messages_dropped"] += 1
        
        return messages_to_forward
    
    def get_stats(self) -> Dict:
        """Get node statistics"""
        energy_stats = self.energy_account.get_stats()
        
        return {
            "node_id": self.node_id,
            "neighbors": len(self.neighbors),
            "energy_balance": energy_stats["balance"],
            "messages_sent": self.stats["messages_sent"],
            "messages_relayed": self.stats["messages_relayed"],
            "messages_received": self.stats["messages_received"],
            "messages_dropped": self.stats["messages_dropped"],
            "relay_queue_size": len(self.relay_queue),
            "is_plugged_in": self.config.is_plugged_in,
        }
    
    def __str__(self) -> str:
        stats = self.get_stats()
        return (f"Node({self.node_id}: {stats['energy_balance']:.0f}j, "
                f"sent={stats['messages_sent']}, relayed={stats['messages_relayed']}, "
                f"received={stats['messages_received']})")


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("MESH NODE SIMULATION")
    print("=" * 60)
    
    # Create three nodes
    alice_config = NodeConfig(node_id="Alice", is_plugged_in=False)
    bob_config = NodeConfig(node_id="Bob", is_plugged_in=True)
    carol_config = NodeConfig(node_id="Carol", is_plugged_in=False)
    
    alice = MeshNode(alice_config)
    bob = MeshNode(bob_config)
    carol = MeshNode(carol_config)
    
    # Set up network topology: Alice -- Bob -- Carol
    network_graph = {
        "Alice": {"Bob"},
        "Bob": {"Alice", "Carol"},
        "Carol": {"Bob"},
    }
    
    alice.update_neighbors({"Bob"})
    alice.update_network_graph(network_graph)
    
    bob.update_neighbors({"Alice", "Carol"})
    bob.update_network_graph(network_graph)
    
    carol.update_neighbors({"Bob"})
    carol.update_network_graph(network_graph)
    
    print("\n📡 NETWORK TOPOLOGY")
    print("   Alice -- Bob -- Carol")
    print("   (Bob is plugged in)")
    
    print("\n📨 Alice sends message to Carol")
    msg = alice.send_message("Carol", "Hello from Alice!")
    
    if msg:
        print(f"   Message created: {msg}")
        print(f"   Energy cost: {msg.energy_cost}j")
        
        # Bob receives and relays
        print(f"\n📡 Bob receives message")
        bob.receive_message(msg)
        print(f"   Bob's balance: {bob.energy_account.balance}j (earned relay reward)")
        
        # Process Bob's relay queue
        to_forward = bob.process_relay_queue()
        if to_forward:
            print(f"   Bob forwards to Carol")
            
            # Carol receives
            for fwd_msg in to_forward:
                carol.receive_message(fwd_msg)
            print(f"   ✅ Carol received message!")
    
    print("\n📊 FINAL STATS")
    for node in [alice, bob, carol]:
        print(f"   {node}")
    
    print("\n✅ Node simulation complete!")
