"""Binary tree data structure for split pane layout."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Union

from src.models.enums import SplitDirection


@dataclass
class PaneLeaf:
    """Terminal leaf node in the pane tree."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Terminal"

    @property
    def is_leaf(self) -> bool:
        return True


@dataclass
class PaneSplit:
    """Split node containing two children."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    direction: SplitDirection = SplitDirection.HORIZONTAL
    ratio: float = 0.5
    first: PaneNode = field(default_factory=PaneLeaf)
    second: PaneNode = field(default_factory=PaneLeaf)

    @property
    def is_leaf(self) -> bool:
        return False


PaneNode = Union[PaneLeaf, PaneSplit]


def get_all_leaves(node: PaneNode) -> list[PaneLeaf]:
    """Return all leaf nodes in the tree."""
    if isinstance(node, PaneLeaf):
        return [node]
    return get_all_leaves(node.first) + get_all_leaves(node.second)


def find_node(root: PaneNode, node_id: str) -> PaneNode | None:
    """Find a node by id."""
    if root.id == node_id:
        return root
    if isinstance(root, PaneSplit):
        return find_node(root.first, node_id) or find_node(root.second, node_id)
    return None


def find_parent(root: PaneNode, node_id: str) -> PaneSplit | None:
    """Find the parent split node of a given node id."""
    if isinstance(root, PaneSplit):
        if root.first.id == node_id or root.second.id == node_id:
            return root
        return find_parent(root.first, node_id) or find_parent(root.second, node_id)
    return None


def replace_node(root: PaneNode, node_id: str, new_node: PaneNode) -> PaneNode:
    """Replace a node by id, returning new tree (immutable)."""
    if root.id == node_id:
        return new_node
    if isinstance(root, PaneSplit):
        return PaneSplit(
            id=root.id,
            direction=root.direction,
            ratio=root.ratio,
            first=replace_node(root.first, node_id, new_node),
            second=replace_node(root.second, node_id, new_node),
        )
    return root
