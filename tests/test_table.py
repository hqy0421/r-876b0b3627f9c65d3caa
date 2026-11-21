#!/usr/bin/env python
import logging
import os
import unittest
from operator import itemgetter

import pytest

import pdfplumber
from pdfplumber import table

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/pdffill-demo.pdf")
        self.pdf = pdfplumber.open(path)

    @classmethod
    def teardown_class(self):
        self.pdf.close()

    def test_orientation_errors(self):
        with pytest.raises(ValueError):
            table.join_edge_group([], "x")

    def test_table_settings_errors(self):
        with pytest.raises(ValueError):
            tf = table.TableFinder(self.pdf.pages[0], tuple())

        with pytest.raises(TypeError):
            tf = table.TableFinder(self.pdf.pages[0], {"strategy": "x"})
            tf.get_edges()

        with pytest.raises(ValueError):
            tf = table.TableFinder(self.pdf.pages[0], {"vertical_strategy": "x"})

        with pytest.raises(ValueError):
            tf = table.TableFinder(
                self.pdf.pages[0],
                {
                    "vertical_strategy": "explicit",
                    "explicit_vertical_lines": [],
                },
            )

        with pytest.raises(ValueError):
            tf = table.TableFinder(self.pdf.pages[0], {"join_tolerance": -1})
            tf.get_edges()

    def test_edges_strict(self):
        path = os.path.join(HERE, "pdfs/issue-140-example.pdf")
        with pdfplumber.open(path) as pdf:
            t = pdf.pages[0].extract_table(
                {
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict",
                }
            )

        assert t[-1] == [
            "",
            "0085648100300",
            "CENTRAL KMA",
            "LILYS 55% DARK CHOC BAR",
            "415",
            "$ 0.61",
            "$ 253.15",
            "0.0000",
            "",
        ]

    def test_rows_and_columns(self):
        path = os.path.join(HERE, "pdfs/issue-140-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            table = page.find_table()
            row = [page.crop(bbox).extract_text() for bbox in table.rows[0].cells]
            assert row == [
                "Line no",
                "UPC code",
                "Location",
                "Item Description",
                "Item Quantity",
                "Bill Amount",
                "Accrued Amount",
                "Handling Rate",
                "PO number",
            ]
            col = [page.crop(bbox).extract_text() for bbox in table.columns[1].cells]
            assert col == [
                "UPC code",
                "0085648100305",
                "0085648100380",
                "0085648100303",
                "0085648100300",
            ]

    def test_explicit_desc_decimalization(self):
        """
        See issue #290
        """
        tf = table.TableFinder(
            self.pdf.pages[0],
            {
                "vertical_strategy": "explicit",
                "explicit_vertical_lines": [100, 200, 300],
                "horizontal_strategy": "explicit",
                "explicit_horizontal_lines": [100, 200, 300],
            },
        )
        assert tf.tables[0].extract()

    def test_text_tolerance(self):
        path = os.path.join(HERE, "pdfs/senate-expenditures.pdf")
        with pdfplumber.open(path) as pdf:
            bbox = (70.332, 130.986, 420, 509.106)
            cropped = pdf.pages[0].crop(bbox)
            t = cropped.extract_table(
                {
                    "horizontal_strategy": "text",
                    "vertical_strategy": "text",
                    "min_words_vertical": 20,
                }
            )
            t_tol = cropped.extract_table(
                {
                    "horizontal_strategy": "text",
                    "vertical_strategy": "text",
                    "min_words_vertical": 20,
                    "text_x_tolerance": 1,
                }
            )
            t_tol_from_tables = cropped.extract_tables(
                {
                    "horizontal_strategy": "text",
                    "vertical_strategy": "text",
                    "min_words_vertical": 20,
                    "text_x_tolerance": 1,
                }
            )[0]

        assert t[-1] == [
            "DHAW20190070",
            "09/09/2019",
            "CITIBANK-TRAVELCBACARD",
            "08/12/2019",
            "08/14/2019",
        ]
        assert t_tol[-1] == [
            "DHAW20190070",
            "09/09/2019",
            "CITIBANK - TRAVEL CBA CARD",
            "08/12/2019",
            "08/14/2019",
        ]
        assert t_tol[-1] == t_tol_from_tables[-1]

    def test_text_layout(self):
        path = os.path.join(HERE, "pdfs/issue-53-example.pdf")
        with pdfplumber.open(path) as pdf:
            table = pdf.pages[0].extract_table(
                {
                    "text_layout": True,
                }
            )
            assert table[3][0] == "   FY2013   \n   FY2014   "

    def test_text_without_words(self):
        assert table.words_to_edges_h([]) == []
        assert table.words_to_edges_v([]) == []

    def test_order(self):
        """
        See issue #336
        """
        path = os.path.join(HERE, "pdfs/issue-336-example.pdf")
        with pdfplumber.open(path) as pdf:
            tables = pdf.pages[0].extract_tables()
            assert len(tables) == 3
            assert len(tables[0]) == 8
            assert len(tables[1]) == 11
            assert len(tables[2]) == 2

    def test_issue_466_mixed_strategy(self):
        """
        See issue #466
        """
        path = os.path.join(HERE, "pdfs/issue-466-example.pdf")
        with pdfplumber.open(path) as pdf:
            tables = pdf.pages[0].extract_tables(
                {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 8,
                    "intersection_tolerance": 4,
                }
            )

            # The engine only extracts the tables which have drawn horizontal
            # lines.
            # For the 3 extracted tables, some common properties are expected:
            # - 4 rows
            # - 3 columns
            # - Data in last row contains the string 'last'
            for t in tables:
                assert len(t) == 4
                assert len(t[0]) == 3

                # Verify that all cell contain real data
                for cell in t[3]:
                    assert "last" in cell

    def test_discussion_539_null_value(self):
        """
        See discussion #539
        """
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            table_settings = {
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "explicit_vertical_lines": [],
                "explicit_horizontal_lines": [],
                "snap_tolerance": 3,
                "join_tolerance": 3,
                "edge_min_length": 3,
                "min_words_vertical": 3,
                "min_words_horizontal": 1,
                "text_keep_blank_chars": False,
                "text_tolerance": 3,
                "intersection_tolerance": 3,
            }
            assert page.extract_table(table_settings)
            assert page.extract_tables(table_settings)

    def test_table_curves(self):
        # See https://github.com/jsvine/pdfplumber/discussions/808
        path = os.path.join(HERE, "pdfs/table-curves-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            assert len(page.curves)
            tables = page.extract_tables()
            assert len(tables) == 1
            t = tables[0]
            assert t[-2][-2] == "Uncommon"

            assert len(page.extract_tables({"vertical_strategy": "lines_strict"})) == 0


def _v(x, top, bottom):
    return {
        "orientation": "v",
        "x0": x,
        "x1": x,
        "top": top,
        "bottom": bottom,
        "width": 0,
        "height": bottom - top,
    }


def _h(y, x0, x1):
    return {
        "orientation": "h",
        "x0": x0,
        "x1": x1,
        "top": y,
        "bottom": y,
        "width": x1 - x0,
        "height": 0,
    }


def _naive_intersections(edges, x_tolerance=1, y_tolerance=1):
    """Straightforward pairwise reference implementation."""
    intersections = {}
    v_edges = [e for e in edges if e["orientation"] == "v"]
    h_edges = [e for e in edges if e["orientation"] == "h"]
    for v in sorted(v_edges, key=itemgetter("x0", "top")):
        for h in sorted(h_edges, key=itemgetter("top", "x0")):
            if (
                v["top"] <= (h["top"] + y_tolerance)
                and v["bottom"] >= (h["top"] - y_tolerance)
                and v["x0"] >= (h["x0"] - x_tolerance)
                and v["x0"] <= (h["x1"] + x_tolerance)
            ):
                vertex = (v["x0"], h["top"])
                if vertex not in intersections:
                    intersections[vertex] = {"v": [], "h": []}
                intersections[vertex]["v"].append(v)
                intersections[vertex]["h"].append(h)
    return intersections


class TestEdgesToIntersections(unittest.TestCase):
    def test_matches_naive_on_exactly_equal_boundaries(self):
        # With zero tolerance, an intersection requires the vertical edge to
        # touch the horizontal edge's endpoints exactly; inclusive boundaries
        # must be kept.
        edges = [
            _h(10, 0, 10),
            _v(0, 0, 10),  # at left endpoint
            _v(10, 0, 10),  # at right endpoint
            _v(5, 0, 10),
            _v(10.0001, 0, 10),  # just outside, no match
        ]
        fast = table.edges_to_intersections(edges, 0, 0)
        naive = _naive_intersections(edges, 0, 0)
        assert list(fast.keys()) == list(naive.keys())
        assert fast == naive
        assert set(fast.keys()) == {(0, 10), (10, 10), (5, 10)}

    def test_matches_naive_with_tolerance(self):
        edges = [
            _h(10, 5, 20),
            _v(4.5, 8, 12),  # within x tolerance, y range covers
            _v(20.5, 11.5, 30),  # within x and y tolerance
            _v(21, 0, 9),  # outside x and y
            _h(12, 4, 6),
        ]
        fast = table.edges_to_intersections(edges, 1, 1)
        naive = _naive_intersections(edges, 1, 1)
        assert list(fast.keys()) == list(naive.keys())
        assert fast == naive

    def test_preserves_duplicate_edges_and_order(self):
        # Two identical vertical edges should both appear in each vertex's "v"
        # list, and the per-vertex edge lists should match the naive ordering.
        v = _v(5, 0, 10)
        edges = [_h(0, 0, 10), _h(10, 0, 10), dict(v), dict(v)]
        fast = table.edges_to_intersections(edges)
        naive = _naive_intersections(edges)
        assert list(fast.keys()) == list(naive.keys())
        assert fast == naive
        assert all(len(entry["v"]) == 2 for entry in fast.values())

    def test_empty_and_single_orientation(self):
        assert table.edges_to_intersections([]) == {}
        assert table.edges_to_intersections([_v(1, 0, 5)]) == {}
        assert table.edges_to_intersections([_h(1, 0, 5)]) == {}

    def test_degenerate_vertical_span(self):
        # A vertical edge whose (tolerance-expanded) span is empty cannot
        # intersect anything, even a horizontal edge at the same coordinate.
        edges = [_h(5, 0, 10), _v(5, 6, 4)]
        assert table.edges_to_intersections(edges, 0, 0) == {}
        assert table.edges_to_intersections(edges, 1, 0) == {}


class TestIntersectionEquivalence(unittest.TestCase):
    """Compare the optimized intersection path against a naive scan over
    randomly generated edge sets, including coincident and boundary cases."""

    def test_random_edge_sets_match_naive(self):
        import random

        rng = random.Random(1234)

        def rand_coord():
            return rng.choice([0, 1, 2, 3, 4, 5, rng.uniform(0, 5)])

        for _ in range(500):
            edges = []
            for _ in range(rng.randint(0, 8)):
                x = rand_coord()
                top = rand_coord()
                bottom = top + rng.choice([0, 1, 2, rng.uniform(0, 5)])
                edges.append(_v(x, top, bottom))
            for _ in range(rng.randint(0, 8)):
                y = rand_coord()
                x0 = rand_coord()
                x1 = x0 + rng.choice([0, 1, 2, rng.uniform(0, 5)])
                edges.append(_h(y, x0, x1))
            rng.shuffle(edges)

            xt = rng.choice([0, 0.5, 1, 2])
            yt = rng.choice([0, 0.5, 1, 2])
            fast = table.edges_to_intersections(edges, xt, yt)
            naive = _naive_intersections(edges, xt, yt)
            assert list(fast.keys()) == list(naive.keys())
            assert fast == naive
