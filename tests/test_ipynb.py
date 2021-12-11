from collections import namedtuple

import pytest

from pytest_split.algorithms import Algorithms
from pytest_split.plugin import _reorganize_broken_up_ipynbs

item = namedtuple("item", "nodeid")


class TestIPyNb:
    @pytest.mark.parametrize("algo_name", ["duration_based_chunks"])
    def test__reorganize_broken_up_ipynbs(self, algo_name):
        durations = {
            "temp/nbs/test_1.ipynb::Cell 0": 1,
            "temp/nbs/test_1.ipynb::Cell 1": 1,
            "temp/nbs/test_1.ipynb::Cell 2": 1,
            "temp/nbs/test_2.ipynb::Cell 0": 3,
            "temp/nbs/test_2.ipynb::Cell 1": 5,
            "temp/nbs/test_2.ipynb::Cell 2": 1,
            "temp/nbs/test_2.ipynb::Cell 3": 4,
            "temp/nbs/test_3.ipynb::Cell 0": 5,
            "temp/nbs/test_3.ipynb::Cell 1": 1,
            "temp/nbs/test_3.ipynb::Cell 2": 1,
            "temp/nbs/test_3.ipynb::Cell 3": 2,
            "temp/nbs/test_3.ipynb::Cell 4": 1,
            "temp/nbs/test_4.ipynb::Cell 0": 1,
            "temp/nbs/test_4.ipynb::Cell 1": 1,
            "temp/nbs/test_4.ipynb::Cell 2": 3
        }
        items = [item(x) for x in durations.keys()]
        algo = Algorithms[algo_name].value
        g1, g2, g3 = algo(splits=3, items=items, durations=durations)
        # pytest.set_trace()
        assert g1.selected == [
            item(nodeid='temp/nbs/test_1.ipynb::Cell 0'),
            item(nodeid='temp/nbs/test_1.ipynb::Cell 1'),
            item(nodeid='temp/nbs/test_1.ipynb::Cell 2'),
            item(nodeid='temp/nbs/test_2.ipynb::Cell 0'),
            item(nodeid='temp/nbs/test_2.ipynb::Cell 1')
        ]
        assert g2.selected == [
            item(nodeid='temp/nbs/test_2.ipynb::Cell 2'),
            item(nodeid='temp/nbs/test_2.ipynb::Cell 3'),
            item(nodeid='temp/nbs/test_3.ipynb::Cell 0'),
            item(nodeid='temp/nbs/test_3.ipynb::Cell 1')
        ]
        assert g3.selected == [
            item(nodeid='temp/nbs/test_3.ipynb::Cell 2'),
            item(nodeid='temp/nbs/test_3.ipynb::Cell 3'),
            item(nodeid='temp/nbs/test_3.ipynb::Cell 4'),
            item(nodeid='temp/nbs/test_4.ipynb::Cell 0'),
            item(nodeid='temp/nbs/test_4.ipynb::Cell 1'),
            item(nodeid='temp/nbs/test_4.ipynb::Cell 2')
        ]

        _reorganize_broken_up_ipynbs(g1, items)
        assert g1.selected == [
            item(nodeid='temp/nbs/test_1.ipynb::Cell 0'),
            item(nodeid='temp/nbs/test_1.ipynb::Cell 1'),
            item(nodeid='temp/nbs/test_1.ipynb::Cell 2'),
            item(nodeid='temp/nbs/test_2.ipynb::Cell 0'),
            item(nodeid='temp/nbs/test_2.ipynb::Cell 1'),
            item(nodeid='temp/nbs/test_2.ipynb::Cell 2'),
            item(nodeid='temp/nbs/test_2.ipynb::Cell 3')
        ]

        _reorganize_broken_up_ipynbs(g2, items)
        assert g2.selected == [
            item(nodeid='temp/nbs/test_3.ipynb::Cell 0'),
            item(nodeid='temp/nbs/test_3.ipynb::Cell 1'),
            item(nodeid='temp/nbs/test_3.ipynb::Cell 2'),
            item(nodeid='temp/nbs/test_3.ipynb::Cell 3'),
            item(nodeid='temp/nbs/test_3.ipynb::Cell 4')
        ]

        _reorganize_broken_up_ipynbs(g3, items)
        assert g3.selected == [
            item(nodeid='temp/nbs/test_4.ipynb::Cell 0'),
            item(nodeid='temp/nbs/test_4.ipynb::Cell 1'),
            item(nodeid='temp/nbs/test_4.ipynb::Cell 2')
        ]
