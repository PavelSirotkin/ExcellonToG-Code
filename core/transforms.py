"""
Координатные преобразования (виртуальные ↔ экранные).
Всегда читает актуальные значения из config.
"""
import core.config as cfg


def clamp_offset(ox, oy, sf):
    """Ограничивает смещение, но только если область просмотра меньше мира."""
    if sf == 0:
        return ox, oy
    vw = cfg.WORKAREA_WIDTH / sf
    vh = cfg.WORKAREA_HEIGHT / sf
    world_w = cfg.X_MAX - cfg.X_MIN
    world_h = cfg.Y_MAX - cfg.Y_MIN
    if vw < world_w:
        ox = max(cfg.X_MIN + vw / 2, min(ox, cfg.X_MAX - vw / 2))
    if vh < world_h:
        oy = max(cfg.Y_MIN + vh / 2, min(oy, cfg.Y_MAX - vh / 2))
    return ox, oy


def to_real_x(virtual_x):
    """Виртуальная X (мм) → экранная X (пиксели)."""
    center_x = cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH / 2
    return center_x + (virtual_x - cfg.offset_x) * cfg.scale_factor


def to_real_y(virtual_y):
    """Виртуальная Y (мм) → экранная Y (пиксели). Инвертирована."""
    center_y = cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT / 2
    return center_y - (virtual_y - cfg.offset_y) * cfg.scale_factor


def to_virtual_x(real_x):
    """Экранная X (пиксели) → виртуальная X (мм)."""
    if cfg.scale_factor == 0:
        return cfg.offset_x
    center_x = cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH / 2
    return cfg.offset_x + (real_x - center_x) / cfg.scale_factor


def to_virtual_y(real_y):
    """Экранная Y (пиксели) → виртуальная Y (мм). Инвертирована."""
    if cfg.scale_factor == 0:
        return cfg.offset_y
    center_y = cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT / 2
    return cfg.offset_y + (center_y - real_y) / cfg.scale_factor
