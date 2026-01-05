"""
Energy Module - Energy accounting and economic incentives
Implements the energy credit system that incentivizes relaying
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json


@dataclass
class EnergyTransaction:
    """A single energy transfer between nodes"""
    transaction_id: str
    timestamp: float
    from_node: str
    to_node: str
    amount: float
    reason: str  # "send", "relay", "receive", "penalty"
    message_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "amount": self.amount,
            "reason": self.reason,
            "message_id": self.message_id,
        }


@dataclass
class EnergyAccount:
    """Energy account for a mesh node"""
    node_id: str
    balance: float = 1000.0  # Starting balance
    total_earned: float = 0.0
    total_spent: float = 0.0
    messages_sent: int = 0
    messages_relayed: int = 0
    messages_received: int = 0
    transactions: List[EnergyTransaction] = field(default_factory=list)
    is_plugged_in: bool = False
    relay_multiplier: float = 1.0  # Plugged-in nodes can relay more
    
    def can_afford(self, amount: float) -> bool:
        """Check if node has enough credits"""
        return self.balance >= amount
    
    def debit(self, amount: float, reason: str, message_id: Optional[str] = None) -> bool:
        """
        Deduct energy credits (for sending messages)
        Returns True if successful, False if insufficient balance
        """
        if not self.can_afford(amount):
            return False
        
        self.balance -= amount
        self.total_spent += amount
        
        if reason == "send":
            self.messages_sent += 1
        
        transaction = EnergyTransaction(
            transaction_id=f"tx_{len(self.transactions)}",
            timestamp=datetime.now().timestamp(),
            from_node=self.node_id,
            to_node="network",
            amount=amount,
            reason=reason,
            message_id=message_id,
        )
        self.transactions.append(transaction)
        
        return True
    
    def credit(self, amount: float, reason: str, from_node: str = "network", 
               message_id: Optional[str] = None):
        """
        Add energy credits (for relaying messages)
        """
        # Apply relay multiplier if plugged in
        if reason == "relay" and self.is_plugged_in:
            amount *= self.relay_multiplier
        
        self.balance += amount
        self.total_earned += amount
        
        if reason == "relay":
            self.messages_relayed += 1
        elif reason == "receive":
            self.messages_received += 1
        
        transaction = EnergyTransaction(
            transaction_id=f"tx_{len(self.transactions)}",
            timestamp=datetime.now().timestamp(),
            from_node=from_node,
            to_node=self.node_id,
            amount=amount,
            reason=reason,
            message_id=message_id,
        )
        self.transactions.append(transaction)
    
    def get_transaction_history(self, limit: int = 10) -> List[Dict]:
        """Get recent transaction history"""
        return [tx.to_dict() for tx in self.transactions[-limit:]]
    
    def get_stats(self) -> Dict:
        """Get account statistics"""
        net_balance_change = self.total_earned - self.total_spent
        
        return {
            "node_id": self.node_id,
            "balance": round(self.balance, 2),
            "total_earned": round(self.total_earned, 2),
            "total_spent": round(self.total_spent, 2),
            "net_change": round(net_balance_change, 2),
            "messages_sent": self.messages_sent,
            "messages_relayed": self.messages_relayed,
            "messages_received": self.messages_received,
            "is_plugged_in": self.is_plugged_in,
            "relay_efficiency": round(self.total_earned / self.messages_relayed, 2) if self.messages_relayed > 0 else 0,
        }


class EnergyMarket:
    """
    Manages energy economics across the entire network
    Implements pricing, incentives, and anti-spam mechanisms
    """
    
    def __init__(self):
        self.accounts: Dict[str, EnergyAccount] = {}
        self.base_send_cost = 100.0  # Cost to send a message
        self.base_relay_reward = 10.0  # Reward for relaying
        self.spam_penalty = 50.0  # Penalty for spamming
        self.total_energy_in_system = 0.0
        
    def create_account(self, node_id: str, initial_balance: float = 1000.0, 
                      is_plugged_in: bool = False) -> EnergyAccount:
        """Create new energy account for a node"""
        account = EnergyAccount(
            node_id=node_id,
            balance=initial_balance,
            is_plugged_in=is_plugged_in,
            relay_multiplier=1.5 if is_plugged_in else 1.0,
        )
        self.accounts[node_id] = account
        self.total_energy_in_system += initial_balance
        return account
    
    def get_account(self, node_id: str) -> Optional[EnergyAccount]:
        """Get account for a node"""
        return self.accounts.get(node_id)
    
    def calculate_send_cost(self, message_size_kb: float, priority: int = 1, 
                           num_hops: int = 3) -> float:
        """
        Calculate cost to send a message
        Factors: size, priority, expected hops
        """
        size_factor = 1.0 + (message_size_kb * 0.1)  # +10% per KB
        priority_factor = [0.5, 1.0, 1.5, 2.0][priority]  # LOW, NORMAL, HIGH, URGENT
        hop_factor = 1.0 + (num_hops * 0.2)  # +20% per hop
        
        cost = self.base_send_cost * size_factor * priority_factor * hop_factor
        return round(cost, 2)
    
    def calculate_relay_reward(self, message_cost: float, is_plugged_in: bool = False) -> float:
        """
        Calculate reward for relaying a message
        Relays get 10% of sender's cost
        Plugged-in nodes get 1.5x multiplier
        """
        reward = message_cost * 0.1
        
        if is_plugged_in:
            reward *= 1.5
        
        return round(reward, 2)
    
    def process_message_send(self, sender_id: str, message_id: str, 
                            message_size_kb: float = 1.0, priority: int = 1, 
                            num_hops: int = 3) -> bool:
        """
        Process energy transaction for sending a message
        Returns True if sender had enough credits
        """
        sender = self.get_account(sender_id)
        if not sender:
            return False
        
        cost = self.calculate_send_cost(message_size_kb, priority, num_hops)
        
        return sender.debit(cost, "send", message_id)
    
    def process_relay(self, relay_node_id: str, message_id: str, 
                     message_cost: float):
        """Process energy reward for relaying a message"""
        relay_node = self.get_account(relay_node_id)
        if not relay_node:
            return
        
        reward = self.calculate_relay_reward(message_cost, relay_node.is_plugged_in)
        relay_node.credit(reward, "relay", from_node="network", message_id=message_id)
    
    def detect_spam(self, node_id: str, time_window_seconds: int = 60, 
                   max_messages: int = 10) -> bool:
        """
        Detect if node is spamming (too many messages in short time)
        Returns True if spam detected
        """
        account = self.get_account(node_id)
        if not account:
            return False
        
        recent_time = datetime.now().timestamp() - time_window_seconds
        recent_sends = [
            tx for tx in account.transactions
            if tx.reason == "send" and tx.timestamp >= recent_time
        ]
        
        return len(recent_sends) > max_messages
    
    def apply_spam_penalty(self, node_id: str):
        """Apply penalty for spamming"""
        account = self.get_account(node_id)
        if account:
            account.debit(self.spam_penalty, "penalty")
    
    def get_network_stats(self) -> Dict:
        """Get overall network energy statistics"""
        if not self.accounts:
            return {}
        
        total_balance = sum(acc.balance for acc in self.accounts.values())
        total_earned = sum(acc.total_earned for acc in self.accounts.values())
        total_spent = sum(acc.total_spent for acc in self.accounts.values())
        total_messages = sum(acc.messages_sent for acc in self.accounts.values())
        total_relays = sum(acc.messages_relayed for acc in self.accounts.values())
        
        # Find top relays
        top_relays = sorted(
            self.accounts.values(),
            key=lambda a: a.messages_relayed,
            reverse=True
        )[:5]
        
        return {
            "total_nodes": len(self.accounts),
            "total_energy": round(total_balance, 2),
            "total_earned": round(total_earned, 2),
            "total_spent": round(total_spent, 2),
            "total_messages": total_messages,
            "total_relays": total_relays,
            "avg_balance": round(total_balance / len(self.accounts), 2),
            "top_relays": [
                {
                    "node_id": acc.node_id,
                    "relayed": acc.messages_relayed,
                    "earned": round(acc.total_earned, 2),
                    "balance": round(acc.balance, 2),
                }
                for acc in top_relays
            ]
        }
    
    def rebalance_energy(self, target_balance: float = 1000.0):
        """
        Periodic rebalancing to prevent energy hoarding
        Give bonus to low-balance nodes, gentle tax on high-balance
        """
        for account in self.accounts.values():
            if account.balance < target_balance * 0.5:
                # Boost struggling nodes
                bonus = (target_balance * 0.5 - account.balance) * 0.1
                account.credit(bonus, "rebalance")
            elif account.balance > target_balance * 2.0:
                # Gentle tax on energy hoarders
                tax = (account.balance - target_balance * 2.0) * 0.05
                account.debit(tax, "rebalance")


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("ENERGY MARKET SIMULATION")
    print("=" * 60)
    
    # Create energy market
    market = EnergyMarket()
    
    # Create accounts
    market.create_account("Alice", is_plugged_in=False)
    market.create_account("Bob", is_plugged_in=True)  # Plugged in = better relay
    market.create_account("Carol", is_plugged_in=False)
    
    print("\n📊 INITIAL BALANCES")
    for node_id, account in market.accounts.items():
        print(f"   {node_id}: {account.balance}j")
    
    # Simulate message sends and relays
    print("\n📨 SIMULATING MESSAGES")
    
    # Alice sends message (costs 100j)
    success = market.process_message_send("Alice", "msg_1", message_size_kb=1.0, num_hops=2)
    print(f"   Alice sends message: {'✅' if success else '❌'}")
    
    # Bob relays (earns reward with 1.5x multiplier because plugged in)
    market.process_relay("Bob", "msg_1", message_cost=100.0)
    print(f"   Bob relays message (plugged in bonus)")
    
    # Carol relays (earns standard reward)
    market.process_relay("Carol", "msg_1", message_cost=100.0)
    print(f"   Carol relays message (standard)")
    
    print("\n⚡ FINAL BALANCES")
    for node_id, account in market.accounts.items():
        stats = account.get_stats()
        print(f"   {node_id}: {stats['balance']}j (earned: {stats['total_earned']}j, spent: {stats['total_spent']}j)")
    
    print("\n🏆 NETWORK STATS")
    network_stats = market.get_network_stats()
    print(f"   Total messages: {network_stats['total_messages']}")
    print(f"   Total relays: {network_stats['total_relays']}")
    print(f"   Average balance: {network_stats['avg_balance']}j")
    
    print("\n💡 KEY INSIGHT:")
    print("   Bob earned MORE than Carol for same relay (plugged-in bonus)")
    print("   This incentivizes keeping phones charged and relaying!")
