import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidgetItem, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6 import uic
from PyQt6.QtCore import QTimer, QTime

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("MainWindow.ui", self)

        self.song_add_btn.clicked.connect(self.add_song)
        self.evnt_add_btn.clicked.connect(self.add_event)
        self.start_btn.clicked.connect(self.start_timer)
        self.stop_btn.clicked.connect(self.stop_timer)

        self.Songs_table.setSelectionBehavior(self.Songs_table.SelectionBehavior.SelectRows)
        self.Songs_table.setEditTriggers(self.Songs_table.EditTrigger.NoEditTriggers)
        self.Songs_table.cellDoubleClicked.connect(self.edit_cell)
        self.Songs_table.currentCellChanged.connect(self.update_event_table)

        self.Event_table.setSelectionBehavior(self.Songs_table.SelectionBehavior.SelectRows)
        self.Event_table.setEditTriggers(self.Songs_table.EditTrigger.NoEditTriggers)
        self.Event_table.cellDoubleClicked.connect(self.edit_cell)
        self.Event_table.currentCellChanged.connect(self.update_event_table)

        self.song_events = {}
        self.Songs_table.setCurrentCell(0, 0)
        # Зелёная подсветка выбранной строки
        self.Songs_table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #429800;
            }
        """)
        self.Event_table.setStyleSheet("""
                    QTableWidget::item:selected {
                        background-color: #69a2c3;
                    }
                """)


        # Таймеры
        self.song_qtimer = QTimer()
        self.song_qtimer.timeout.connect(self.update_song_timer)

        self.show_qtimer = QTimer()
        self.show_qtimer.timeout.connect(self.update_show_timer)

        # Время начала
        self.song_elapsed = QTime(0, 0, 0)
        self.show_target_time = None

        self.show_event_list = []  # Список (время, имя, индекс строки)
        self.current_event_index = 0

    def add_song(self):
        table = self.Songs_table
        row_position = table.rowCount()
        table.insertRow(row_position)

        # 1. Порядковый номер
        item_number = QTableWidgetItem(str(row_position + 1))
        item_number.setFlags(item_number.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row_position, 0, item_number)

        # 2. Название песни (пустая, редактируемая)
        item_title = QTableWidgetItem("")
        table.setItem(row_position, 1, item_title)
        table.setCurrentCell(row_position, 1)
        table.editItem(item_title)

        # 3. Длительность по умолчанию
        item_duration = QTableWidgetItem("00:00")
        table.setItem(row_position, 2, item_duration)

        # Инициализация пустого списка событий
        self.song_events[row_position] = []

    def update_event_table(self, current_row, *_):
        """Обновить таблицу событий при выборе песни"""
        self.highlight_selected_row(current_row)

        events = self.song_events.get(current_row, [])
        self.Event_table.setRowCount(0)

        for event in events:
            row_pos = self.Event_table.rowCount()
            self.Event_table.insertRow(row_pos)
            for col, value in enumerate(event):
                self.Event_table.setItem(row_pos, col, QTableWidgetItem(value))

    def highlight_selected_row(self, row):
        self.Songs_table.selectRow(row)

    def edit_cell(self, row, column):
        item = self.Songs_table.item(row, column)
        if item:
            self.Songs_table.editItem(item)

    def add_event(self):
        song_row = self.Songs_table.currentRow()
        if song_row < 0:
            return

        events = self.song_events.setdefault(song_row, [])

        # Убедимся, что столбцы установлены
        if self.Event_table.columnCount() < 3:
            self.Event_table.setColumnCount(3)

        event_index = len(events) + 1
        current_time_str = self.song_elapsed.toString("mm:ss")

        new_event = [str(event_index), "", current_time_str]
        events.append(new_event)

        self.Event_table.setRowCount(len(events))
        for col, value in enumerate(new_event):
            item = QTableWidgetItem(value)
            self.Event_table.setItem(len(events) - 1, col, item)

        self.Event_table.setCurrentCell(len(events) - 1, 1)
        item_to_edit = self.Event_table.item(len(events) - 1, 1)
        if item_to_edit:
            self.Event_table.editItem(item_to_edit)

    def start_timer(self):
        row = self.Songs_table.currentRow()
        if row < 0:
            return

        duration_item = self.Songs_table.item(row, 2)
        if not duration_item:
            return

        duration_str = duration_item.text()

        if duration_str == "00:00":
            # Старт секундомера
            self.song_elapsed = QTime(0, 0, 0)
            self.song_qtimer.start(1000)
        else:
            # Есть длительность — запускаем обратный отсчёт до ближайшего события
            self.prepare_show_timer_to_event()
            self.show_qtimer.start(1000)



    def stop_timer(self):
        self.song_qtimer.stop()
        self.show_qtimer.stop()

        row = self.Songs_table.currentRow()
        if row < 0:
            return

        if self.Songs_table.item(row, 2).text() == "00:00":
            self.Songs_table.setItem(row, 2, QTableWidgetItem(self.song_elapsed.toString("mm:ss")))

        # Записываем результат в колонку "длительность"
        duration_str = self.song_elapsed.toString("mm:ss")
        self.Songs_table.setItem(row, 2, QTableWidgetItem(duration_str))

    def update_song_timer(self):
        self.song_elapsed = self.song_elapsed.addSecs(1)
        self.song_timer.setText(self.song_elapsed.toString("mm:ss"))  # QLabel

    def update_show_timer(self):
        self.song_elapsed = self.song_elapsed.addSecs(1)

        if not self.show_target_time:
            return

        remaining = self.song_elapsed.secsTo(self.show_target_time)
        if remaining <= 0:
            # Событие наступило
            self.current_event_index += 1
            self.set_current_event_target()
            return

        mins, secs = divmod(remaining, 60)
        self.show_timer.setText(f"{mins:02d}:{secs:02d}")

    def prepare_show_timer_to_event(self):
        row = self.Songs_table.currentRow()
        if row < 0:
            return

        events = self.song_events.get(row, [])
        if not events:
            return

        # Собираем валидные события
        self.show_event_list = []
        for idx, e in enumerate(events):
            try:
                t = QTime.fromString(e[2], "mm:ss")
                if t.isValid():
                    self.show_event_list.append((t, e[1], idx))  # (время, имя, индекс строки)
            except:
                continue

        if not self.show_event_list:
            return

        # Сортируем события по времени
        self.show_event_list.sort()
        self.current_event_index = 0

        # Устанавливаем первый таймер
        self.song_elapsed = QTime(0, 0, 0)
        self.set_current_event_target()

    def set_current_event_target(self):
        if self.current_event_index >= len(self.show_event_list):
            self.show_qtimer.stop()
            self.show_timer.setText("00:00")
            self.Show_Event.setText("🎵 Конец событий")
            return

        self.show_target_time, event_name, row_index = self.show_event_list[self.current_event_index]

        # Обновляем название события
        self.Show_Event.setText(f"⏰ {event_name}")

        # Подсвечиваем строку в таблице Event_table
        self.highlight_event_row(row_index)

    def highlight_event_row(self, row):
        self.Event_table.selectRow(row)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
