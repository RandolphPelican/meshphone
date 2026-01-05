"""
Routing Module - AODV-inspired route discovery
Ad-hoc On-Demand Distance Vector routing for mesh networks
"""

from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from collections import deque


@dataclass
class RouteEntry:
    """A single route in the routing table"""
    destination: str
    next_hop: str
    hop_count: int
    sequence_number: int
    is_active: bool = True


class Router:
    """
    Implements simplified AODV routing for mesh networks
    
    Key features:
    - On-demand route discovery (only when needed)
    - Loop-free routing (via sequence numbers)
    - Handles node mobility (route expiration)
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.routing_table: Dict[str, RouteEntry] = {}
        self.sequence_number = 0
        self.neighbors: Set[str] = set()
        
    def update_neighbors(self, neighbors: Set[str]):
        """Update list of directly reachable neighbors"""
        self.neighbors = neighbors
        
        # Invalidate routes through disconnected neighbors
        for dest, route in list(self.routing_table.items()):
            if route.next_hop not in self.neighbors:
                route.is_active = False
    
    def find_route(self, destination: str, 
                   network_graph: Dict[str, Set[str]]) -> Optional[List[str]]:
        """
        Find shortest path to destination using BFS
        
        Args:
            destination: Target node ID
            network_graph: Dict mapping node_id -> set of neighbor IDs
            
        Returns:
            List of node IDs representing the path, or None if no route
        """
        if self.node_id == destination:
            return [self.node_id]
        
        if destination not in network_graph:
            return None
        
        # Breadth-first search for shortest path
        visited = {self.node_id}
        queue = deque([(self.node_id, [self.node_id])])
        
        while queue:
            current, path = queue.popleft()
            
            for neighbor in network_graph.get(current, set()):
                if neighbor == destination:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def cache_route(self, destination: str, path: List[str]):
        """
        Cache a discovered route in routing table
        Used for route optimization (avoid repeated discovery)
        """
        if len(path) < 2:
            return
        
        # Find where we are in the path
        try:
            my_index = path.index(self.node_id)
        except ValueError:
            return
        
        if my_index >= len(path) - 1:
            return
        
        next_hop = path[my_index + 1]
        hop_count = len(path) - my_index - 1
        
        self.sequence_number += 1
        
        self.routing_table[destination] = RouteEntry(
            destination=destination,
            next_hop=next_hop,
            hop_count=hop_count,
            sequence_number=self.sequence_number,
            is_active=True
        )
    
    def get_cached_route(self, destination: str) -> Optional[str]:
        """
        Get next hop from cached routing table
        Returns None if no valid cached route exists
        """
        route = self.routing_table.get(destination)
        
        if route and route.is_active and route.next_hop in self.neighbors:
            return route.next_hop
        
        return None
    
    def invalidate_route(self, destination: str):
        """Mark a route as invalid (link broken, node moved, etc)"""
        if destination in self.routing_table:
            self.routing_table[destination].is_active = False
