import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from minidb.btree import BTree


def test_insert_and_search():
    bt = BTree(t=2)
    for i in [10, 20, 5, 6, 12, 30, 7, 17]:
        bt.insert(i, f"val{i}")
    for i in [10, 20, 5, 6, 12, 30, 7, 17]:
        assert bt.search(i) == f"val{i}"
    assert bt.search(999) is None


def test_update_existing_key():
    bt = BTree(t=2)
    bt.insert(1, "a")
    bt.insert(1, "b")
    assert bt.search(1) == "b"
    assert len(bt) == 1


def test_in_order_is_sorted():
    bt = BTree(t=3)
    keys = random.sample(range(1000), 100)
    for k in keys:
        bt.insert(k, k * 10)
    result = bt.in_order()
    assert [k for k, _ in result] == sorted(keys)
    assert len(bt) == 100


def test_range_query():
    bt = BTree(t=3)
    for i in range(50):
        bt.insert(i, i)
    result = bt.range_query(10, 20)
    assert [k for k, _ in result] == list(range(10, 21))


def test_delete_leaf_key():
    bt = BTree(t=2)
    for i in [5, 10, 15, 20, 25]:
        bt.insert(i, i)
    assert bt.delete(15) is True
    assert bt.search(15) is None
    assert len(bt) == 4
    assert bt.delete(999) is False


def test_large_random_insert_and_lookup():
    bt = BTree(t=4)
    keys = list(range(500))
    random.shuffle(keys)
    for k in keys:
        bt.insert(k, f"v{k}")
    for k in range(500):
        assert bt.search(k) == f"v{k}"
    assert len(bt) == 500


if __name__ == "__main__":
    test_insert_and_search()
    test_update_existing_key()
    test_in_order_is_sorted()
    test_range_query()
    test_delete_leaf_key()
    test_large_random_insert_and_lookup()
    print("All BTree tests passed.")
