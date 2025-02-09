Описание программы

Excellon to G-Code Converter — это программа для преобразования файлов сверловки в формате 
Excellon (*.drl, .txt) в управляющий G-код для ЧПУ-станков. 

Основные возможности:

Визуализация отверстий и инструментов с цветовой дифференциацией.

Оптимизация маршрута сверления (алгоритм ближайшего соседа).

Настройка параметров G-кода: глубина, скорость подачи, безопасна высота, позиция парковки.

Масштабирование, панорамирование и отображение сетки/линеек.

Экспорт результатов в формате G-Code (.tap) с возможностью проверки в симуляторе.

Инструкция пользователя

1. Загрузка файла

Нажмите «Выбрать файл» и укажите Excellon-файл.

Если файл не загружается, проверьте:

Формат координат (настройка в верхнем правом углу).

Соответствие структуры файла стандарту Excellon.

2. Работа с интерфейсом

Масштабирование: Колесо мыши.

Панорамирование: Зажмите левую кнопку мыши на холсте и перемещайте.

Легенда (правая панель):

Чекбоксы включают/выключают отображение отверстий для каждого инструмента.

Цвета соответствуют инструментам, указанным в файле.

Опция «Отобразить пути» показывает оптимизированные траектории сверления.

3. Настройка параметров G-кода

Заполните поля в правой панели:

Z: Глубина сверления (отрицательное значение, например, -2.0).

R: Высота безопасного перемещения (например, 5 мм).

F: Скорость подачи инструмента (мм/мин).

P: Высота парковки шпинделя после завершения работы.

4. Генерация G-кода

Нажмите «Создать G-code».

Укажите путь для сохранения файла (.tap).

После успешного сохранения откроется окно с ссылкой на NC Viewer для проверки кода.

Примечания

Формат координат: Выбирается в выпадающем списке (например, 4.2 = 4 знака до точки, 2 после). Если отверстия отображаются некорректно, измените формат.

Рабочая зона: Программа автоматически определяет границы. Отверстия за пределами зоны X: ±300 мм, Y: ±200 мм выделяются предупреждением.

Оптимизация маршрута: Программа минимизирует холостые перемещения, что сокращает время обработки.
