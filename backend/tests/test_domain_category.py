"""Tests domain Category + enum CategoryNature."""
from __future__ import annotations

import pytest

from app.domain.category import Category, CategoryNature


class TestCategoryNature:

    def test_values(self):
        assert CategoryNature.NEED.value == "NEED"
        assert CategoryNature.WANT.value == "WANT"
        assert CategoryNature.SAVING.value == "SAVING"

    def test_from_string(self):
        assert CategoryNature("NEED") == CategoryNature.NEED

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            CategoryNature("RANDOM")


class TestCategoryCreate:

    def test_nominal_without_nature(self):
        c = Category.create(id="c1", name="Logement")
        assert c.id == "c1"
        assert c.name == "Logement"
        assert c.nature is None

    def test_nominal_with_nature(self):
        c = Category.create(id="c1", name="Logement", nature=CategoryNature.NEED)
        assert c.nature == CategoryNature.NEED

    def test_nature_can_be_null(self):
        c = Category.create(id="c1", name="X", nature=None)
        assert c.nature is None

    def test_strips_name_and_id(self):
        c = Category.create(id=" c1 ", name="  X  ")
        assert c.id == "c1"
        assert c.name == "X"

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError):
            Category.create(id="", name="X")

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            Category.create(id="c1", name="   ")

    def test_invalid_nature_type_rejected(self):
        with pytest.raises(ValueError):
            Category.create(id="c1", name="X", nature="NEED")  # type: ignore[arg-type]

    def test_immutable(self):
        c = Category.create(id="c1", name="X")
        with pytest.raises(Exception):
            c.name = "Y"  # type: ignore[misc]
