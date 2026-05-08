"""
Тесты для core/tool_database.py и core/mode_engine.py.
"""
import pytest
import os
import json
from core.tool_database import ToolDatabase, _fmt_key
from core.mode_engine import ModeEngine

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'test_tools_db.json')


class TestFmtKey:
    def test_integer(self):
        assert _fmt_key(1.0) == "1.0"

    def test_one_decimal(self):
        assert _fmt_key(1.5) == "1.5"

    def test_two_decimals(self):
        assert _fmt_key(1.25) == "1.25"

    def test_trailing_zero(self):
        assert _fmt_key(1.50) == "1.5"

    def test_three_decimals(self):
        assert _fmt_key(1.234) == "1.23"


class TestToolDatabase:
    def setup_method(self):
        self.db = ToolDatabase()

    def test_empty_db(self):
        assert self.db.count() == (0, 0)

    def test_add_drill(self):
        result = self.db.add_drill(1.0, spindle_speed=10000, plunge_feed=100,
                                    retract_feed=500)
        assert result is not None
        assert result["diameter"] == 1.0
        assert self.db.count() == (1, 0)

    def test_add_drill_invalid_diameter(self):
        result = self.db.add_drill(-1.0)
        assert result is None

    def test_add_endmill(self):
        result = self.db.add_endmill(2.0, spindle_speed=15000, cutting_feed=50, stepover=50)
        assert result is not None
        assert result["diameter"] == 2.0
        assert self.db.count() == (0, 1)

    def test_find_drill_exact(self):
        self.db.add_drill(1.0, spindle_speed=10000)
        found = self.db.find_drill(1.0)
        assert found is not None
        assert found["spindle_speed"] == 10000

    def test_find_drill_tolerance(self):
        self.db.add_drill(1.0)
        found = self.db.find_drill(1.0005)
        assert found is not None

    def test_find_drill_not_found(self):
        self.db.add_drill(1.0)
        found = self.db.find_drill(5.0)
        assert found is None

    def test_find_endmill_exact(self):
        self.db.add_endmill(2.0, cutting_feed=50)
        found = self.db.find_endmill(2.0)
        assert found is not None
        assert found["cutting_feed"] == 50

    def test_delete_drill(self):
        self.db.add_drill(1.0)
        assert self.db.delete_drill(1.0) is True
        assert self.db.count() == (0, 0)

    def test_delete_drill_not_exists(self):
        assert self.db.delete_drill(99.0) is False

    def test_delete_endmill(self):
        self.db.add_endmill(2.0)
        assert self.db.delete_endmill(2.0) is True

    def test_find_endmill_smaller_than_found(self):
        self.db.add_endmill(1.0, cutting_feed=50)
        found = self.db.find_endmill_smaller_than(3.0)
        assert found is not None
        assert found["diameter"] == 1.0

    def test_find_endmill_smaller_than_not_found(self):
        self.db.add_endmill(3.0)
        found = self.db.find_endmill_smaller_than(3.0)
        assert found is None

    def test_find_endmill_smaller_than_returns_largest(self):
        self.db.add_endmill(1.0)
        self.db.add_endmill(2.0)
        found = self.db.find_endmill_smaller_than(3.0)
        assert found is not None
        assert found["diameter"] == 2.0

    def test_find_endmill_smaller_than_exact_not_included(self):
        self.db.add_endmill(2.0)
        found = self.db.find_endmill_smaller_than(2.0)
        assert found is None

    def test_update_drill(self):
        self.db.add_drill(1.0, spindle_speed=10000)
        self.db.update_drill(1.0, spindle_speed=12000)
        found = self.db.find_drill(1.0)
        assert found["spindle_speed"] == 12000

    def test_update_drill_not_exists(self):
        result = self.db.update_drill(99.0, spindle_speed=100)
        assert result is None

    # ---- extra_depth (Pro-режим: per-tool доп. глубина сверления) ----

    def test_add_drill_extra_depth_stored(self):
        result = self.db.add_drill(3.0, spindle_speed=15000, plunge_feed=200,
                                   retract_feed=500, extra_depth=1.0)
        assert result is not None
        assert result["extra_depth"] == 1.0
        # Сохранилось при поиске
        assert self.db.find_drill(3.0)["extra_depth"] == 1.0

    def test_add_drill_extra_depth_default_zero(self):
        # Не передаём extra_depth — должно быть 0 (через цикл-дополнение DRILL_FIELDS)
        result = self.db.add_drill(1.0, spindle_speed=10000)
        assert result is not None
        assert result["extra_depth"] == 0

    def test_update_drill_extra_depth(self):
        self.db.add_drill(2.0, spindle_speed=10000)
        assert self.db.find_drill(2.0)["extra_depth"] == 0
        self.db.update_drill(2.0, extra_depth=0.5)
        assert self.db.find_drill(2.0)["extra_depth"] == 0.5

    def test_set_tool_params_drills_forwards_extra_depth(self):
        # Compat-обёртка set_tool_params должна пробрасывать extra_depth
        # в add_drill — иначе поле молча теряется при использовании этого пути.
        ok = self.db.set_tool_params("drills", "1.0", {
            "diameter": 1.0, "spindle_speed": 10000, "feed_rate": 100,
            "extra_depth": 0.7,
        })
        assert ok is True
        assert self.db.find_drill(1.0)["extra_depth"] == 0.7

    def test_legacy_drill_record_without_extra_depth(self):
        # JSON старого формата (до introduction of extra_depth): поле отсутствует.
        # Загрузка должна пройти; чтение через .get(...) даёт 0 как default.
        legacy_json = '{"drills": {"1.0": {"diameter": 1.0, "spindle_speed": 10000, "plunge_feed": 100, "retract_feed": 500}}, "endmills": {}}'
        assert self.db.import_json(legacy_json) is True
        rec = self.db.find_drill(1.0)
        assert rec is not None
        # Запись в JSON без поля; .get(... ,0) даёт 0.
        assert rec.get("extra_depth", 0) == 0

    def test_get_all_sorted(self):
        self.db.add_drill(3.0)
        self.db.add_drill(1.0)
        self.db.add_drill(2.0)
        drills = self.db.get_all_drills()
        assert [d["diameter"] for d in drills] == [1.0, 2.0, 3.0]

    def test_clear(self):
        self.db.add_drill(1.0)
        self.db.add_endmill(2.0)
        self.db.clear()
        assert self.db.count() == (0, 0)

    def test_export_import(self):
        self.db.add_drill(1.0, spindle_speed=10000)
        self.db.add_endmill(2.0, cutting_feed=50)
        json_str = self.db.export_json()
        new_db = ToolDatabase()
        assert new_db.import_json(json_str) is True
        assert new_db.count() == (1, 1)
        assert new_db.find_drill(1.0) is not None
        assert new_db.find_endmill(2.0) is not None

    def test_save_load_file(self):
        path = TEST_DB_PATH
        self.db.add_drill(1.0, spindle_speed=10000)
        assert self.db.save(path) is True
        new_db = ToolDatabase()
        assert new_db.load(path) is True
        assert new_db.count() == (1, 0)
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    def test_load_nonexistent_creates_empty(self):
        # Новая логика: создаёт пустую базу если файла нет
        path = os.path.join(os.path.dirname(__file__), 'fixtures', 'temp_test_db.json')
        if os.path.exists(path):
            os.remove(path)
        result = self.db.load(path)
        assert result is True
        assert self.db.count() == (0, 0)
        # Cleanup
        if os.path.exists(path):
            os.remove(path)


class TestModeEngine:
    def setup_method(self):
        self.engine = ModeEngine()

    def test_default_mode(self):
        assert self.engine.mode == "simple"
        assert self.engine.is_simple is True
        assert self.engine.is_pro is False

    def test_toggle(self):
        self.engine.toggle()
        assert self.engine.is_pro is True
        self.engine.toggle()
        assert self.engine.is_simple is True

    def test_set_mode(self):
        self.engine.mode = "pro"
        assert self.engine.is_pro is True

    def test_set_invalid_mode(self):
        with pytest.raises(ValueError):
            self.engine.mode = "invalid"

    def test_simple_drill_params(self):
        global_params = {"safe_z": 5.0, "drill_z": -2.5, "feed_rate": 100, "rapid_rate": 500, "park_z": 30}
        result = self.engine.get_drill_params(1.0, global_params)
        assert result == global_params

    def test_pro_drill_params_found(self):
        self.engine.mode = "pro"
        self.engine.tool_db.add_drill(1.0, spindle_speed=12000, plunge_feed=80, retract_feed=600)
        global_params = {"safe_z": 5.0, "drill_z": -2.5, "feed_rate": 100, "rapid_rate": 500, "park_z": 30}
        result = self.engine.get_drill_params(1.0, global_params)
        assert result is not None
        assert result["spindle_speed"] == 12000
        assert result["feed_rate"] == 80

    def test_pro_drill_params_not_found(self):
        self.engine.mode = "pro"
        global_params = {"safe_z": 5.0, "drill_z": -2.5, "feed_rate": 100, "rapid_rate": 500, "park_z": 30}
        result = self.engine.get_drill_params(99.0, global_params)
        assert result is None

    def test_pro_drill_params_includes_extra_depth(self):
        # Pro-режим: extra_depth из карточки сверла должен попадать в
        # возвращаемый словарь параметров (используется gcode_generator).
        self.engine.mode = "pro"
        self.engine.tool_db.add_drill(3.0, spindle_speed=15000, plunge_feed=200,
                                      retract_feed=500, extra_depth=1.0)
        global_params = {"safe_z": 5.0, "drill_z": -2.5, "feed_rate": 100, "rapid_rate": 500, "park_z": 30}
        result = self.engine.get_drill_params(3.0, global_params)
        assert result is not None
        assert result["extra_depth"] == 1.0

    def test_pro_drill_params_extra_depth_defaults_zero(self):
        # Сверло в базе без явного extra_depth — get_drill_params возвращает 0.
        self.engine.mode = "pro"
        self.engine.tool_db.add_drill(1.0, spindle_speed=10000)
        global_params = {"safe_z": 5.0, "drill_z": -2.5, "feed_rate": 100, "rapid_rate": 500, "park_z": 30}
        result = self.engine.get_drill_params(1.0, global_params)
        assert result is not None
        assert result["extra_depth"] == 0.0

    def test_needs_tool_dialog_simple(self):
        assert self.engine.needs_tool_dialog(1.0, "drill") is False

    def test_needs_tool_dialog_pro_found(self):
        self.engine.mode = "pro"
        self.engine.tool_db.add_drill(1.0)
        assert self.engine.needs_tool_dialog(1.0, "drill") is False

    def test_needs_tool_dialog_pro_not_found(self):
        self.engine.mode = "pro"
        assert self.engine.needs_tool_dialog(99.0, "drill") is True

    def test_pro_endmill_params_found(self):
        self.engine.mode = "pro"
        self.engine.tool_db.add_endmill(2.0, spindle_speed=15000, cutting_feed=50)
        global_params = {"safe_z": 5.0, "drill_z": -2.5, "feed_rate": 100, "mill_feed": 50, "rapid_rate": 500, "park_z": 30}
        result = self.engine.get_endmill_params(2.0, global_params)
        assert result is not None
        assert result["spindle_speed"] == 15000
        assert result["mill_feed"] == 50
        assert result["feed_rate"] == 100  # берётся из global_params

    def test_pro_endmill_params_not_found(self):
        self.engine.mode = "pro"
        global_params = {"safe_z": 5.0, "drill_z": -2.5, "feed_rate": 100, "mill_feed": 50, "rapid_rate": 500, "park_z": 30}
        result = self.engine.get_endmill_params(99.0, global_params)
        assert result is None
