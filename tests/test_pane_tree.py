"""Tests for pane tree data structure."""

from src.models.enums import SplitDirection
from src.models.pane_tree import (
    PaneLeaf,
    PaneSplit,
    find_node,
    find_parent,
    get_all_leaves,
    replace_node,
)


def test_leaf_is_leaf():
    leaf = PaneLeaf(id="a", name="T1")
    assert leaf.is_leaf is True


def test_split_is_not_leaf():
    split = PaneSplit(
        id="s1",
        direction=SplitDirection.HORIZONTAL,
        first=PaneLeaf(id="a"),
        second=PaneLeaf(id="b"),
    )
    assert split.is_leaf is False


def test_get_all_leaves():
    tree = PaneSplit(
        id="s1",
        first=PaneLeaf(id="a"),
        second=PaneSplit(
            id="s2",
            first=PaneLeaf(id="b"),
            second=PaneLeaf(id="c"),
        ),
    )
    leaves = get_all_leaves(tree)
    assert [l.id for l in leaves] == ["a", "b", "c"]


def test_find_node():
    tree = PaneSplit(
        id="s1",
        first=PaneLeaf(id="a"),
        second=PaneLeaf(id="b"),
    )
    assert find_node(tree, "a").id == "a"
    assert find_node(tree, "s1").id == "s1"
    assert find_node(tree, "nope") is None


def test_find_parent():
    tree = PaneSplit(
        id="s1",
        first=PaneLeaf(id="a"),
        second=PaneLeaf(id="b"),
    )
    parent = find_parent(tree, "b")
    assert parent.id == "s1"
    assert find_parent(tree, "s1") is None


def test_replace_node():
    tree = PaneSplit(
        id="s1",
        first=PaneLeaf(id="a"),
        second=PaneLeaf(id="b"),
    )
    new_tree = replace_node(tree, "b", PaneLeaf(id="c", name="New"))
    leaves = get_all_leaves(new_tree)
    assert [l.id for l in leaves] == ["a", "c"]
    # Original tree unchanged
    assert get_all_leaves(tree)[1].id == "b"
