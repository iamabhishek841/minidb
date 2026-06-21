"""
B-Tree implementation used internally by MiniDB as the index structure
for primary keys and indexed columns.

Why a B-Tree (and not a plain dict)?
- A dict gives O(1) point lookups but cannot answer range queries
  (e.g. WHERE age > 30) efficiently -- you'd have to scan everything.
- A B-Tree keeps keys sorted across nodes, so point lookups are
  O(log n) and range scans are O(log n + k) where k is the number
  of matching results.

This is a classic "order-t" B-Tree (CLRS style):
- Every node has at most (2t - 1) keys and at least (t - 1) keys
  (except the root).
- Keys inside a node are kept sorted.
- All leaves are at the same depth.

Each key stores an associated value (here: the row's data, or a
reference to it), so this doubles as a key->value index.
"""

from bisect import bisect_left, insort


class BTreeNode:
    __slots__ = ("keys", "values", "children", "leaf")

    def __init__(self, leaf=True):
        self.keys = []        # sorted list of keys
        self.values = []      # values[i] corresponds to keys[i]
        self.children = []    # only used when leaf is False
        self.leaf = leaf


class BTree:
    """
    Minimal but functional B-Tree supporting insert, search, delete,
    and ordered range queries.

    t = minimum degree (t >= 2). Each node holds between t-1 and 2t-1 keys.
    """

    def __init__(self, t=4):
        if t < 2:
            raise ValueError("Minimum degree t must be >= 2")
        self.t = t
        self.root = BTreeNode(leaf=True)
        self._size = 0

    def __len__(self):
        return self._size

    # ------------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------------
    def search(self, key):
        """Return the value for `key`, or None if not found. O(log n)."""
        return self._search(self.root, key)

    def _search(self, node, key):
        i = bisect_left(node.keys, key)
        if i < len(node.keys) and node.keys[i] == key:
            return node.values[i]
        if node.leaf:
            return None
        return self._search(node.children[i], key)

    def range_query(self, low=None, high=None):
        """
        Return [(key, value), ...] for all keys with low <= key <= high,
        in sorted order. Either bound can be None (open-ended).
        O(log n + k).
        """
        results = []
        self._range_query(self.root, low, high, results)
        return results

    def _range_query(self, node, low, high, results):
        i = 0
        n = len(node.keys)
        while i < n:
            if not node.leaf:
                self._range_query(node.children[i], low, high, results)
            key = node.keys[i]
            if (low is None or key >= low) and (high is None or key <= high):
                results.append((key, node.values[i]))
            i += 1
        if not node.leaf:
            self._range_query(node.children[n], low, high, results)

    # ------------------------------------------------------------------
    # INSERT
    # ------------------------------------------------------------------
    def insert(self, key, value):
        """Insert or update key->value. O(log n)."""
        root = self.root
        if len(root.keys) == 2 * self.t - 1:
            new_root = BTreeNode(leaf=False)
            new_root.children.append(root)
            self._split_child(new_root, 0)
            self.root = new_root
        existed = self._insert_non_full(self.root, key, value)
        if not existed:
            self._size += 1

    def _split_child(self, parent, i):
        t = self.t
        child = parent.children[i]
        new_node = BTreeNode(leaf=child.leaf)

        mid_key = child.keys[t - 1]
        mid_val = child.values[t - 1]

        new_node.keys = child.keys[t:]
        new_node.values = child.values[t:]
        child.keys = child.keys[:t - 1]
        child.values = child.values[:t - 1]

        if not child.leaf:
            new_node.children = child.children[t:]
            child.children = child.children[:t]

        parent.children.insert(i + 1, new_node)
        parent.keys.insert(i, mid_key)
        parent.values.insert(i, mid_val)

    def _insert_non_full(self, node, key, value):
        i = bisect_left(node.keys, key)
        if i < len(node.keys) and node.keys[i] == key:
            node.values[i] = value  # update existing key
            return True

        if node.leaf:
            node.keys.insert(i, key)
            node.values.insert(i, value)
            return False

        if len(node.children[i].keys) == 2 * self.t - 1:
            self._split_child(node, i)
            if key > node.keys[i]:
                i += 1
            elif key == node.keys[i]:
                node.values[i] = value
                return True
        return self._insert_non_full(node.children[i], key, value)

    # ------------------------------------------------------------------
    # DELETE (simplified: remove from leaf directly, or replace with
    # in-order predecessor for internal nodes; no rebalancing/merging
    # for brevity -- documented as a known limitation, see README).
    # ------------------------------------------------------------------
    def delete(self, key):
        """Delete key if present. Returns True if a key was removed."""
        removed = self._delete(self.root, key)
        if removed:
            self._size -= 1
        return removed

    def _delete(self, node, key):
        i = bisect_left(node.keys, key)
        if i < len(node.keys) and node.keys[i] == key:
            if node.leaf:
                node.keys.pop(i)
                node.values.pop(i)
            else:
                # Replace with in-order predecessor (max of left subtree)
                pred_node = node.children[i]
                while not pred_node.leaf:
                    pred_node = pred_node.children[-1]
                node.keys[i] = pred_node.keys[-1]
                node.values[i] = pred_node.values[-1]
                self._delete(node.children[i], pred_node.keys[-1])
            return True
        if node.leaf:
            return False
        return self._delete(node.children[i], key)

    def in_order(self):
        """Return all (key, value) pairs in sorted key order."""
        return self.range_query(None, None)
