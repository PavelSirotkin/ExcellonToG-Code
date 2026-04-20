"""
Движок переключения режимов работы приложения.
Управляет режимом "Простой" / "Про" и поиском параметров инструментов.
"""
from typing import Dict, Any, Optional
from core.tool_database import ToolDatabase


class ModeEngine:
    """Движок режимов. В режиме "pro" использует ToolDatabase для поиска параметров."""

    def __init__(self):
        self._mode: str = "simple"  # "simple" | "pro"
        self.tool_db = ToolDatabase()

    @property
    def mode(self) -> str:
        """Текущий режим: 'simple' или 'pro'."""
        return self._mode

    @mode.setter
    def mode(self, value: str):
        if value in ("simple", "pro"):
            self._mode = value
        else:
            raise ValueError(f"Недопустимый режим: {value}")

    @property
    def is_pro(self) -> bool:
        """True если режим 'pro'."""
        return self._mode == "pro"

    @property
    def is_simple(self) -> bool:
        """True если режим 'simple'."""
        return self._mode == "simple"

    def toggle(self):
        """Переключить режим."""
        self.mode = "pro" if self._mode == "simple" else "simple"

    # ==========================================================
    # Получение параметров инструмента
    # ==========================================================

    def get_drill_params(self, diameter: float,
                         global_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Получить параметры сверла для генерации G-code.

        В режиме 'simple' — всегда возвращает global_params.
        В режиме 'pro' — ищет в базе по диаметру.
            Если найдено — возвращает параметры из базы.
            Если нет — возвращает None (нужен диалог ввода).
        """
        if self.is_simple:
            return global_params

        # pro режим — поиск в базе
        tool = self.tool_db.find_drill(diameter)
        if tool is None:
            return None

        return {
            "spindle_speed": tool.get("spindle_speed", global_params.get("spindle_speed", 10000)),
            "feed_rate": tool.get("plunge_feed", global_params.get("feed_rate", 100)),
            "rapid_rate": tool.get("retract_feed", global_params.get("rapid_rate", 500)),
            "safe_z": global_params.get("safe_z", 5.0),
            "drill_z": global_params.get("drill_z", -2.5),
            "park_z": global_params.get("park_z", 30),
        }

    def get_endmill_params(self, diameter: float,
                           global_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Получить параметры фрезы для генерации G-code.

        В режиме 'simple' — всегда возвращает global_params.
        В режиме 'pro' — ищет в базе по диаметру.
            Если найдено — возвращает параметры из базы.
            Если нет — возвращает None (нужен диалог ввода).
        """
        if self.is_simple:
            return global_params

        # pro режим — поиск в базе
        tool = self.tool_db.find_endmill(diameter)
        if tool is None:
            return None

        return {
            "spindle_speed": tool.get("spindle_speed", global_params.get("spindle_speed", 15000)),
            "feed_rate": global_params.get("feed_rate", 80),
            "mill_feed": tool.get("cutting_feed", global_params.get("mill_feed", 50)),
            "stepover": tool.get("stepover", diameter * 0.5),
            "depth_per_pass": tool.get("depth_per_pass", abs(global_params.get("drill_z", -2.5))),
            "rapid_rate": global_params.get("rapid_rate", 500),
            "safe_z": global_params.get("safe_z", 5.0),
            "drill_z": global_params.get("drill_z", -2.5),
            "park_z": global_params.get("park_z", 30),
        }

    def get_endmill_params_for_slot(self, slot_diameter: float,
                                    global_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Получить параметры фрезы для фрезеровки слота.

        В режиме 'simple' — возвращает global_params (multi_pass=False).
        В режиме 'pro':
          - Точное совпадение → обычные параметры, multi_pass=False.
          - Нет точного, но есть меньший → параметры меньшей фрезы, multi_pass=True.
          - Нет ничего → None.
        """
        if self.is_simple:
            return {**global_params, "multi_pass": False}

        # Точное совпадение
        tool = self.tool_db.find_endmill(slot_diameter)
        if tool is not None:
            return {
                "spindle_speed": tool.get("spindle_speed", global_params.get("spindle_speed", 15000)),
                "feed_rate": global_params.get("feed_rate", 80),
                "mill_feed": tool.get("cutting_feed", global_params.get("mill_feed", 50)),
                "stepover": tool.get("stepover", slot_diameter * 0.5),
                "rapid_rate": global_params.get("rapid_rate", 500),
                "safe_z": global_params.get("safe_z", 5.0),
                "drill_z": global_params.get("drill_z", -2.5),
                "park_z": global_params.get("park_z", 30),
                "multi_pass": False,
                "diameter": slot_diameter,
            }

        # Меньший инструмент
        smaller = self.tool_db.find_endmill_smaller_than(slot_diameter)
        if smaller is not None:
            tool_d = float(smaller["diameter"])
            return {
                "spindle_speed": smaller.get("spindle_speed", global_params.get("spindle_speed", 15000)),
                "feed_rate": global_params.get("feed_rate", 80),
                "mill_feed": smaller.get("cutting_feed", global_params.get("mill_feed", 50)),
                "stepover": smaller.get("stepover", 50),
                "rapid_rate": global_params.get("rapid_rate", 500),
                "safe_z": global_params.get("safe_z", 5.0),
                "drill_z": global_params.get("drill_z", -2.5),
                "park_z": global_params.get("park_z", 30),
                "multi_pass": True,
                "slot_width": slot_diameter,
                "diameter": tool_d,
            }

        return None

    def needs_tool_dialog(self, diameter: float, tool_type: str) -> bool:
        """
        Проверить, нужен ли диалог ввода параметров для инструмента.
        Всегда False в 'simple' режиме.
        В 'pro' режиме — True если инструмент не найден в базе.
        """
        if self.is_simple:
            return False
        if tool_type == "drill":
            return self.tool_db.find_drill(diameter) is None
        elif tool_type == "endmill":
            if self.tool_db.find_endmill(diameter) is not None:
                return False
            return self.tool_db.find_endmill_smaller_than(diameter) is None
        return False
