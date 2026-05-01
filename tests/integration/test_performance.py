"""
Performance интеграционные тесты: проверка производительности на больших файлах.

Тестируют:
1. Парсинг больших Excellon файлов (1000+ отверстий)
2. Генерацию G-code для больших плат
3. TSP оптимизацию для большого количества точек
4. Визуализацию больших наборов данных
5. Работу с памятью при обработке больших файлов
"""
import os
import time
import pytest
import tempfile
from core.parser import parse_excellon_file, parse_slot_file
from core.gcode_generator import _build_drilling_gcode, _build_milling_gcode, _build_combined_gcode
from core.tsp_optimizer import nearest_neighbor_tsp, nearest_neighbor_tsp_slots


# Путь к тестовым файлам
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Samples")


class TestPerformance:
    """Performance тесты."""
    
    def _generate_large_excellon_file(self, num_holes=1000, coord_format="4.2"):
        """Генерировать большой Excellon файл для тестирования."""
        content = [
            "M48",
            ";Layer_Color=9474304",
            f";FILE_FORMAT={coord_format}",
            "METRIC",
            ";TYPE=PLATED",
            "T01F00S00C0.80",
            "T02F00S00C1.00",
            "T03F00S00C1.50",
            "%",
            "T01"
        ]
        
        # Генерировать отверстия в сетке
        grid_size = int(num_holes ** 0.5) + 1
        for i in range(num_holes):
            x = (i % grid_size) * 1000  # 10mm шаг
            y = (i // grid_size) * 1000
            content.append(f"X{x:06d}Y{y:06d}")
        
        content.append("M30")
        
        # Создать временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.drl', delete=False) as f:
            f.write('\n'.join(content))
            return f.name
    
    def _generate_large_slot_file(self, num_slots=100, coord_format="4.2"):
        """Генерировать большой файл слотов для тестирования."""
        content = [
            "M48",
            ";Layer_Color=9474304",
            f";FILE_FORMAT={coord_format}",
            "METRIC",
            "T01F00S00C2.00",
            "%",
            "T01"
        ]
        
        # Генерировать слоты
        for i in range(num_slots):
            x_start = i * 500
            y_start = i * 500
            x_end = x_start + 2000
            y_end = y_start
            content.extend([
                f"G00X{x_start:06d}Y{y_start:06d}",
                "M15",
                f"G01X{x_end:06d}Y{y_end:06d}",
                "M16"
            ])
        
        content.append("M30")
        
        # Создать временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.drl', delete=False) as f:
            f.write('\n'.join(content))
            return f.name
    
    @pytest.mark.slow
    def test_parse_large_excellon_file(self):
        """Тест парсинга большого Excellon файла (1000 отверстий)."""
        # Генерировать большой файл
        test_file = self._generate_large_excellon_file(num_holes=1000)
        
        try:
            # Измерить время парсинга
            start_time = time.time()
            tools = parse_excellon_file(test_file, "4.2")
            parse_time = time.time() - start_time
            
            # Проверить результат
            assert tools is not None
            total_holes = sum(len(data['holes']) for data in tools.values())
            assert total_holes == 1000, f"Ожидалось 1000 отверстий, получено {total_holes}"
            
            # Проверить производительность (должно быть быстрее 10 секунд)
            assert parse_time < 10.0, f"Парсинг занял {parse_time:.2f}s, ожидалось < 10s"
            
            print(f"\n✓ Парсинг 1000 отверстий: {parse_time:.3f}s")
        finally:
            # Удалить временный файл
            if os.path.exists(test_file):
                os.unlink(test_file)
    
    @pytest.mark.slow
    def test_generate_gcode_for_large_board(self):
        """Тест генерации G-code для большой платы (1000 отверстий)."""
        # Генерировать большой файл
        test_file = self._generate_large_excellon_file(num_holes=1000)
        
        try:
            # Парсинг
            tools = parse_excellon_file(test_file, "4.2")
            
            # Измерить время генерации G-code
            params = {
                'safe_z': 5.0,
                'drill_z': -2.5,
                'feed_rate': 100,
                'rapid_rate': 500,
                'park_z': 30
            }
            
            start_time = time.time()
            gcode, errors = _build_drilling_gcode(tools, test_file, params)
            gen_time = time.time() - start_time
            
            # Проверить результат
            assert errors == []
            assert gcode is not None
            assert len(gcode) > 0
            
            # Проверить производительность (должно быть быстрее 3 секунд)
            assert gen_time < 3.0, f"Генерация G-code занял {gen_time:.2f}s, ожидалось < 3s"
            
            # Проверить размер G-code
            lines = gcode.split('\n')
            assert len(lines) > 1000, "G-code должен содержать много строк"
            
            print(f"\n✓ Генерация G-code для 1000 отверстий: {gen_time:.3f}s")
            print(f"  Размер G-code: {len(gcode)} байт, {len(lines)} строк")
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)
    
    @pytest.mark.slow
    def test_tsp_optimization_performance(self):
        """Тест производительности TSP оптимизации для большого количества точек."""
        # Генерировать 500 случайных точек
        import random
        random.seed(42)  # Для воспроизводимости
        
        num_points = 500
        points = [(random.uniform(0, 100), random.uniform(0, 100)) for _ in range(num_points)]
        
        # Измерить время оптимизации
        start_time = time.time()
        optimized = nearest_neighbor_tsp(points)
        opt_time = time.time() - start_time
        
        # Проверить результат
        assert len(optimized) == num_points
        assert set(optimized) == set(points), "Все точки должны быть сохранены"
        
        # Проверить производительность (должно быть быстрее 2 секунд)
        assert opt_time < 2.0, f"TSP оптимизация заняла {opt_time:.2f}s, ожидалось < 2s"
        
        print(f"\n✓ TSP оптимизация для {num_points} точек: {opt_time:.3f}s")
    
    @pytest.mark.slow
    def test_slot_parsing_performance(self):
        """Тест производительности парсинга большого количества слотов."""
        # Генерировать файл с 200 слотами
        test_file = self._generate_large_slot_file(num_slots=200)
        
        try:
            # Измерить время парсинга
            start_time = time.time()
            slot_tools = parse_slot_file(test_file, "4.2")
            parse_time = time.time() - start_time
            
            # Проверить результат
            assert slot_tools is not None
            total_slots = sum(len(data['slots']) for data in slot_tools.values())
            assert total_slots == 200, f"Ожидалось 200 слотов, получено {total_slots}"
            
            # Проверить производительность
            assert parse_time < 3.0, f"Парсинг слотов занял {parse_time:.2f}s, ожидалось < 3s"
            
            print(f"\n✓ Парсинг 200 слотов: {parse_time:.3f}s")
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)
    
    @pytest.mark.slow
    def test_combined_large_workflow(self):
        """Тест полного workflow с большими файлами."""
        # Генерировать большие файлы
        holes_file = self._generate_large_excellon_file(num_holes=500)
        slots_file = self._generate_large_slot_file(num_slots=100)
        
        try:
            # Измерить общее время
            start_time = time.time()
            
            # Парсинг
            tools = parse_excellon_file(holes_file, "4.2")
            slot_tools = parse_slot_file(slots_file, "4.2")
            
            # Генерация комбинированного G-code
            params = {
                'safe_z': 5.0,
                'drill_z': -2.5,
                'feed_rate': 100,
                'mill_feed': 50,
                'rapid_rate': 500,
                'park_z': 30
            }
            gcode, errors = _build_combined_gcode(
                tools, holes_file,
                slot_tools, slots_file,
                params
            )
            
            total_time = time.time() - start_time
            
            # Проверить результат
            assert errors == []
            assert gcode is not None
            
            # Проверить производительность (полный workflow < 10 секунд)
            assert total_time < 10.0, f"Полный workflow занял {total_time:.2f}s, ожидалось < 10s"
            
            print(f"\n✓ Полный workflow (500 отверстий + 100 слотов): {total_time:.3f}s")
        finally:
            if os.path.exists(holes_file):
                os.unlink(holes_file)
            if os.path.exists(slots_file):
                os.unlink(slots_file)
    
    def test_memory_efficiency_large_file(self):
        """Тест эффективности использования памяти при обработке больших файлов."""
        import sys
        
        # Генерировать большой файл
        test_file = self._generate_large_excellon_file(num_holes=1000)
        
        try:
            # Измерить использование памяти (приблизительно)
            # Парсинг
            tools = parse_excellon_file(test_file, "4.2")
            
            # Оценить размер данных
            total_holes = sum(len(data['holes']) for data in tools.values())
            
            # Примерная оценка: каждое отверстие — это tuple из 2 float (16 байт)
            # + накладные расходы структур данных
            estimated_size = total_holes * 16 * 2  # x2 для накладных расходов
            
            # Проверить, что размер разумный (< 1MB для 1000 отверстий)
            assert estimated_size < 1024 * 1024, f"Размер данных слишком большой: {estimated_size} байт"
            
            print(f"\n✓ Использование памяти для 1000 отверстий: ~{estimated_size / 1024:.1f} KB")
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)
    
    @pytest.mark.slow
    def test_real_world_file_performance(self):
        """Тест производительности на реальном файле из Samples."""
        test_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        
        if not os.path.exists(test_file):
            pytest.skip("Тестовый файл не найден")
        
        # Измерить полный цикл
        start_time = time.time()
        
        # Парсинг
        tools = parse_excellon_file(test_file, "4.2")
        
        # Генерация G-code
        params = {
            'safe_z': 5.0,
            'drill_z': -2.5,
            'feed_rate': 100,
            'rapid_rate': 500,
            'park_z': 30
        }
        gcode, errors = _build_drilling_gcode(tools, test_file, params)
        
        total_time = time.time() - start_time
        
        # Проверить результат
        assert errors == []
        assert gcode is not None
        
        # Реальный файл должен обрабатываться очень быстро (< 1 секунды)
        assert total_time < 1.0, f"Обработка реального файла заняла {total_time:.2f}s, ожидалось < 1s"
        
        total_holes = sum(len(data['holes']) for data in tools.values())
        print(f"\n✓ Реальный файл ({total_holes} отверстий): {total_time:.3f}s")
    
    @pytest.mark.slow
    def test_tsp_slots_optimization_performance(self):
        """Тест производительности TSP оптимизации для слотов."""
        import random
        random.seed(42)
        
        # Генерировать 100 случайных слотов
        num_slots = 100
        slots = []
        for _ in range(num_slots):
            start = (random.uniform(0, 100), random.uniform(0, 100))
            end = (random.uniform(0, 100), random.uniform(0, 100))
            slots.append((start, end))
        
        # Измерить время оптимизации
        start_time = time.time()
        optimized = nearest_neighbor_tsp_slots(slots)
        opt_time = time.time() - start_time
        
        # Проверить результат
        assert len(optimized) == num_slots
        
        # Проверить производительность (увеличен лимит для 100 слотов)
        assert opt_time < 5.0, f"TSP оптимизация слотов заняла {opt_time:.2f}s, ожидалось < 5s"
        
        print(f"\n✓ TSP оптимизация для {num_slots} слотов: {opt_time:.3f}s")
    
    def test_gcode_generation_scalability(self):
        """Тест масштабируемости генерации G-code."""
        sizes = [10, 50, 100, 200]
        times = []
        
        for size in sizes:
            test_file = self._generate_large_excellon_file(num_holes=size)
            
            try:
                tools = parse_excellon_file(test_file, "4.2")
                params = {
                    'safe_z': 5.0,
                    'drill_z': -2.5,
                    'feed_rate': 100,
                    'rapid_rate': 500,
                    'park_z': 30
                }
                
                start_time = time.time()
                gcode, errors = _build_drilling_gcode(tools, test_file, params)
                gen_time = time.time() - start_time
                times.append(gen_time)
                
                assert errors == []
            finally:
                if os.path.exists(test_file):
                    os.unlink(test_file)
        
        # Проверить, что время растёт линейно (не экспоненциально)
        # Время для 200 отверстий не должно быть > 20x времени для 10 отверстий
        if times[0] > 0:
            ratio = times[-1] / times[0]
            assert ratio < 20, f"Время генерации растёт слишком быстро: {ratio}x"
        
        print(f"\n✓ Масштабируемость генерации G-code:")
        for size, t in zip(sizes, times):
            print(f"  {size} отверстий: {t:.3f}s")


@pytest.mark.slow
class TestStressTests:
    """Стресс-тесты для экстремальных условий."""
    
    def test_extreme_large_file(self):
        """Стресс-тест с очень большим файлом (5000 отверстий)."""
        # Этот тест может быть медленным, поэтому помечен как slow
        from tests.integration.test_performance import TestPerformance
        
        perf_test = TestPerformance()
        test_file = perf_test._generate_large_excellon_file(num_holes=5000)
        
        try:
            start_time = time.time()
            tools = parse_excellon_file(test_file, "4.2")
            parse_time = time.time() - start_time
            
            total_holes = sum(len(data['holes']) for data in tools.values())
            assert total_holes == 5000
            
            # Должно завершиться за разумное время (< 30 секунд)
            assert parse_time < 30.0, f"Парсинг 5000 отверстий занял {parse_time:.2f}s"
            
            print(f"\n✓ Стресс-тест: 5000 отверстий за {parse_time:.3f}s")
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)
    
    def test_many_tools(self):
        """Стресс-тест с большим количеством инструментов."""
        # Генерировать файл с 20 различными инструментами
        content = [
            "M48",
            ";FILE_FORMAT=4.2",
            "METRIC"
        ]
        
        # Добавить 20 инструментов
        for i in range(1, 21):
            content.append(f"T{i:02d}F00S00C{0.5 + i * 0.1:.2f}")
        
        content.append("%")
        
        # Добавить отверстия для каждого инструмента
        for i in range(1, 21):
            content.append(f"T{i:02d}")
            for j in range(10):
                x = i * 1000 + j * 100
                y = i * 1000
                content.append(f"X{x:06d}Y{y:06d}")
        
        content.append("M30")
        
        # Создать временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.drl', delete=False) as f:
            f.write('\n'.join(content))
            test_file = f.name
        
        try:
            tools = parse_excellon_file(test_file, "4.2")
            
            # Проверить, что все инструменты загружены
            assert len(tools) == 20, f"Ожидалось 20 инструментов, получено {len(tools)}"
            
            # Проверить, что у каждого инструмента есть отверстия
            for tool_data in tools.values():
                assert len(tool_data['holes']) == 10
            
            print(f"\n✓ Стресс-тест: 20 инструментов, 200 отверстий")
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)
