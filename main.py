
import sys
import json
import re
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QTimer, QTime
from PyQt6 import uic

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Проверка существования MainWindow.ui
        ui_path = "MainWindow.ui"
        if not os.path.exists(ui_path):
            QMessageBox.critical(self, "Ошибка", f"Файл {ui_path} не найден в {os.getcwd()}")
            sys.exit(1)

        try:
            uic.loadUi(ui_path, self)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить UI: {str(e)}")
            sys.exit(1)

        # Map UI elements
        self.Songs_table = self.findChild(QTableWidget, "Songs_table")
        self.Event_table = self.findChild(QTableWidget, "Event_table")
        self.song_add_btn = self.findChild(QPushButton, "song_add_btn")
        self.song_rmv_btn = self.findChild(QPushButton, "song_rmv_btn")
        self.evnt_add_btn = self.findChild(QPushButton, "evnt_add_btn")
        self.evnt_rmv_btn = self.findChild(QPushButton, "evnt_rmv_btn")
        self.start_btn = self.findChild(QPushButton, "start_btn")
        self.stop_btn = self.findChild(QPushButton, "stop_btn")
        self.song_timer = self.findChild(QLabel, "song_timer")
        self.show_timer = self.findChild(QLabel, "show_timer")
        self.Show_Event = self.findChild(QLabel, "Show_Event")
        self.show_name = self.findChild(QLineEdit, "Show_Name")


        # Connect buttons
        self.song_add_btn.clicked.connect(self.add_song)
        self.song_rmv_btn.clicked.connect(self.delete_song)
        self.evnt_add_btn.clicked.connect(self.add_event)
        self.evnt_rmv_btn.clicked.connect(self.delete_event)
        self.start_btn.clicked.connect(self.start_timer)
        self.stop_btn.clicked.connect(self.stop_timer)

        # Connect menu actions
        save_action = self.findChild(QAction, "actionSave_Show")
        open_action = self.findChild(QAction, "actionOpen_Show")
        if save_action:
            save_action.triggered.connect(self.save_show)
        if open_action:
            open_action.triggered.connect(self.open_show)

        # Table setup
        self.Songs_table.setColumnCount(3)
        self.Event_table.setColumnCount(3)
        self.Songs_table.setSelectionBehavior(self.Songs_table.SelectionBehavior.SelectRows)
        self.Songs_table.setEditTriggers(self.Songs_table.EditTrigger.NoEditTriggers)
        self.Songs_table.cellDoubleClicked.connect(self.edit_song_cell)
        self.Songs_table.currentCellChanged.connect(self.update_event_table)
        self.Songs_table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #429800;
                color: white;
            }
        """)

        self.Event_table.setSelectionBehavior(self.Event_table.SelectionBehavior.SelectRows)
        self.Event_table.setEditTriggers(self.Event_table.EditTrigger.NoEditTriggers)
        self.Event_table.cellDoubleClicked.connect(self.edit_event_cell)
        self.Event_table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #69a2c3;
                color: white;
            }
        """)

        # Timer setup
        self.song_qtimer = QTimer()
        self.song_qtimer.timeout.connect(self.update_song_timer)
        self.show_qtimer = QTimer()
        self.show_qtimer.timeout.connect(self.update_show_timer)
        self.song_elapsed = QTime(0, 0, 0)
        self.show_target_time = None
        self.song_events = {}
        self.show_event_list = []
        self.current_event_index = 0

        # Enable mouse tracking for reset
        self.song_timer.setMouseTracking(True)
        self.song_timer.mouseDoubleClickEvent = lambda event: self.reset_timer()

        # Initialize with a song
        self.add_song()
        self.Songs_table.setCurrentCell(0, 1)

    def add_song(self):
        """Добавить новую песню в таблицу."""
        table = self.Songs_table
        row_position = table.rowCount()
        table.insertRow(row_position)

        # Индекс песни
        item_number = QTableWidgetItem(str(row_position + 1))
        item_number.setFlags(item_number.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row_position, 0, item_number)

        # Название песни
        item_title = QTableWidgetItem("")
        table.setItem(row_position, 1, item_title)

        # Длительность
        item_duration = QTableWidgetItem("00:00")
        table.setItem(row_position, 2, item_duration)

        self.song_events[row_position] = []
        table.setCurrentCell(row_position, 1)
        table.editItem(item_title)

    def delete_song(self):
        """Удалить выбранную песню."""
        row = self.Songs_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите песню для удаления")
            return

        self.Songs_table.removeRow(row)
        del self.song_events[row]

        # Обновить индексы песен
        for i in range(self.Songs_table.rowCount()):
            item = QTableWidgetItem(str(i + 1))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.Songs_table.setItem(i, 0, item)

        # Обновить таблицу событий
        self.update_event_table(self.Songs_table.currentRow())

    def add_event(self):
        """Добавить событие для выбранной песни."""
        song_row = self.Songs_table.currentRow()
        if song_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите песню")
            return

        events = self.song_events.setdefault(song_row, [])
        event_index = len(events) + 1
        current_time_str = self.song_elapsed.toString("mm:ss")

        # Событие: [название, время]
        new_event = [str(event_index), f"Событие {event_index}", current_time_str]
        events.append(new_event)

        self.Event_table.setRowCount(len(events))
        for col, value in enumerate(new_event):
            item = QTableWidgetItem(value)
            self.Event_table.setItem(len(events) - 1, col, item)

        self.Event_table.setCurrentCell(len(events) - 1, 0)
        item_to_edit = self.Event_table.item(len(events) - 1, 0)
        if item_to_edit:
            self.Event_table.editItem(item_to_edit)

    def delete_event(self):
        """Удалить выбранное событие."""
        song_row = self.Songs_table.currentRow()
        event_row = self.Event_table.currentRow()
        if song_row < 0 or event_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите событие для удаления")
            return

        self.Event_table.removeRow(event_row)
        self.song_events[song_row].pop(event_row)

    def edit_song_cell(self, row, column):
        """Редактировать ячейку таблицы песен."""
        if column != 0:  # Редактировать только название и длительность
            item = self.Songs_table.item(row, column)
            if item:
                if column == 2:  # Валидация времени
                    text = item.text()
                    if not re.match(r"^[0-5][0-9]:[0-5][0-9]$", text):
                        QMessageBox.warning(self, "Ошибка", "Формат времени: mm:ss (00:00-59:59)")
                        item.setText("00:00")
                        return
                self.Songs_table.editItem(item)

    def edit_event_cell(self, row, column):
        """Редактировать ячейку таблицы событий."""
        item = self.Event_table.item(row, column)
        if item:
            if column == 2:  # Валидация времени
                text = item.text()
                if not re.match(r"^[0-5][0-9]:[0-5][0-9]$", text):
                    QMessageBox.warning(self, "Ошибка", "Формат времени: mm:ss (00:00-59:59)")
                    item.setText("00:00")
                    return
            self.Event_table.editItem(item)

    def update_event_table(self, current_row, *_,):
        """Обновить таблицу событий при выборе песни."""
        if current_row >= 0:
            self.Songs_table.selectRow(current_row)
            events = self.song_events.get(current_row, [])
            self.Event_table.setRowCount(0)

            for event in events:
                row_pos = self.Event_table.rowCount()
                self.Event_table.insertRow(row_pos)
                for col, value in enumerate(event):
                    self.Event_table.setItem(row_pos, col, QTableWidgetItem(value))

    def start_timer(self):
        """Запустить таймер."""
        row = self.Songs_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите песню")
            return

        duration_item = self.Songs_table.item(row, 2)
        if not duration_item:
            return

        duration_str = duration_item.text()

        if duration_str == "00:00":
            self.song_elapsed = QTime(0, 0, 0)
            self.song_qtimer.start(1000)
        else:
            self.prepare_show_timer_to_event([2])
            self.show_qtimer.start(1000)

    def stop_timer(self):
        """Остановить таймер."""
        self.song_qtimer.stop()
        self.show_qtimer.stop()

        row = self.Songs_table.currentRow()
        if row < 0:
            return

        # Если работал секундомер — записываем длительность
        if self.song_qtimer.isActive() or not self.show_event_list:
            duration_str = self.song_elapsed.toString("mm:ss")
            self.Songs_table.setItem(row, 2, QTableWidgetItem(duration_str))

        # Сброс состояния
        self.song_elapsed = QTime(0, 0, 0)
        self.song_timer.setText("00:00")
        self.show_timer.setText("00:00")
        self.Show_Event.setText("Событие")
        self.show_target_time = None
        self.current_event_index = 0
        self.show_event_list = []

    def reset_timer(self):
        """Сбросить таймер."""
        self.song_qtimer.stop()
        self.show_qtimer.stop()
        self.song_elapsed = QTime(0, 0, 0)
        self.song_timer.setText("00:00")
        self.Show_Event.setText("Событие")

    def update_song_timer(self):
        """Обновить секундомер."""
        self.song_elapsed = self.song_elapsed.addSecs(1)
        self.song_timer.setText(self.song_elapsed.toString("mm:ss"))

    def update_show_timer(self):
        """Обновить таймер обратного отсчёта до следующего события."""
        self.song_elapsed = self.song_elapsed.addSecs(1)

        if not self.show_target_time:
            return

        remaining = self.song_elapsed.secsTo(self.show_target_time)

        if remaining > 0:
            # Обратный отсчёт до следующего события
            mins, secs = divmod(remaining, 60)
            self.show_timer.setText(f"{mins:02d}:{secs:02d}")
            self.song_timer.setText(self.song_elapsed.toString("mm:ss"))
        else:
            # Событие наступило — обновляем и не делаем обратный отсчёт
            self.current_event_index += 1
            self.set_current_event_target()

    def prepare_show_timer_to_event(self):
        """Подготовить таймер для событий."""
        row = self.Songs_table.currentRow()
        if row < 0:
            return

        events = self.song_events.get(row, [])
        if not events:
            return

        self.show_event_list = []
        for idx, e in enumerate(events):
            try:
                t = QTime.fromString(e[1], "mm:ss")
                if t.isValid():
                    self.show_event_list.append((t, e[0], idx))
            except:
                continue

        if not self.show_event_list:
            return

        self.show_event_list.sort()
        self.current_event_index = 0
        self.song_elapsed = QTime(0, 0, 0)
        self.set_current_event_target()

    def set_current_event_target(self):
        """Установить следующее событие."""
        while self.current_event_index < len(self.show_event_list):
            target_time, event_name, row_index = self.show_event_list[self.current_event_index]
            if target_time > self.song_elapsed:
                self.show_target_time = target_time
                self.Show_Event.setText(f"⏰ {event_name}")
                self.Event_table.selectRow(row_index)
                return
            else:
                # если событие уже в прошлом — пропускаем
                self.current_event_index += 1

        # Все события пройдены
        self.show_qtimer.stop()
        self.show_timer.setText("00:00")
        self.Show_Event.setText("🎵 Конец событий")

    def save_show(self):
        """Сохранить шоу в JSON."""
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить шоу", "", "JSON файлы (*.json)")
        if not file_name:
            return

        data = {
            "show_name": self.show_name.text(),
            "songs": [],
            "song_events": {str(k): v for k, v in self.song_events.items()}
        }

        for row in range(self.Songs_table.rowCount()):
            song = {
                "index": self.Songs_table.item(row, 0).text(),
                "title": self.Songs_table.item(row, 1).text() or "",
                "duration": self.Songs_table.item(row, 2).text()
            }
            data["songs"].append(song)

        try:
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "Успех", "Шоу успешно сохранено")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить шоу: {str(e)}")

    def open_show(self):
        """Загрузить шоу из JSON."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Открыть шоу", "", "JSON файлы (*.json)")
        if not file_name:
            return

        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.show_name.setText(data.get("show_name", ""))
            self.Songs_table.setRowCount(0)
            self.song_events = {}
            for k, v in data.get("song_events", {}).items():
                try:
                    self.song_events[int(k)] = v
                except ValueError:
                    continue

            for song in data.get("songs", []):
                row_position = self.Songs_table.rowCount()
                self.Songs_table.insertRow(row_position)
                for col, key in enumerate(["index", "title", "duration"]):
                    item = QTableWidgetItem(song[key])
                    if col == 0:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.Songs_table.setItem(row_position, col, item)

            self.Songs_table.setCurrentCell(0, 1)
            self.update_event_table(0)
            QMessageBox.information(self, "Успех", "Шоу успешно загружено")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())