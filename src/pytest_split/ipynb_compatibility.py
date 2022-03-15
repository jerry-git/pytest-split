from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List

    from pytest_split.algorithms import TestGroup


def ensure_ipynb_compatibility(group: "TestGroup", items: list) -> None:
    """
    Ensures that group doesn't contain partial IPy notebook cells.

    ``pytest-split`` might, in principle, break up the cells of an
    IPython notebook into different test groups, in which case the tests
    most likely fail (for starters, libraries are imported in Cell 0, so
    all subsequent calls to the imported libraries in the following cells
    will raise ``NameError``).

    """
    if not group.selected or not _is_ipy_notebook(group.selected[0].nodeid):
        return

    item_node_ids = [item.nodeid for item in items]

    # Deal with broken up notebooks at the beginning of the test group
    first = group.selected[0].nodeid
    siblings = _find_sibiling_ipynb_cells(first, item_node_ids)
    if first != siblings[0]:
        for item in list(group.selected):
            if item.nodeid in siblings:
                group.deselected.append(item)
                group.selected.remove(item)

    if not group.selected or not _is_ipy_notebook(group.selected[-1].nodeid):
        return

    # Deal with broken up notebooks at the end of the test group
    last = group.selected[-1].nodeid
    siblings = _find_sibiling_ipynb_cells(last, item_node_ids)
    if last != siblings[-1]:
        for item in list(group.deselected):
            if item.nodeid in siblings:
                group.deselected.remove(item)
                group.selected.append(item)


def _find_sibiling_ipynb_cells(
    ipynb_node_id: str, item_node_ids: "List[str]"
) -> "List[str]":
    """
    Returns all sibling IPyNb cells given an IPyNb cell nodeid.
    """
    fpath = ipynb_node_id.split("::")[0]
    return [item for item in item_node_ids if fpath in item]


def _is_ipy_notebook(node_id: str) -> bool:
    """
    Returns True if node_id is an IPython notebook, otherwise False.
    """
    fpath = node_id.split("::")[0]
    return fpath.endswith(".ipynb")
