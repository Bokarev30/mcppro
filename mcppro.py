import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import json
from PIL import Image, ImageTk, ImageOps
import cv2
import threading
from tkinter import ttk
import time

class MediaControlApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Media Control Panel PRO")
        self.geometry("1920x1080")
        
        # Настройка темы
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Данные приложения
        self.playlist = []  # Теперь будет хранить словари: {'path': '', 'duration': 0}
        self.current_file_index = None
        self.connected = False
        self.preview_image = None
        self.video_capture = None
        self.playing_video = False
        self.after_id = None
        self.playing_playlist = False
        self.playlist_timer = None
        self.current_file_start_time = None
        self.fullscreen_window = None
        self.fullscreen_capture = None
        self.fullscreen_playing = False
        
        # Создание виджетов
        self.create_widgets()
        
        # Запуск обновления видео
        self.update_video_preview()
        
        # Обработка горячих клавиш
        self.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.bind('<Escape>', lambda e: self.stop_fullscreen() if self.fullscreen_playing else None)
    
    def create_widgets(self):
        # Главный фрейм с сеткой
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Верхняя панель управления
        control_frame = ctk.CTkFrame(main_frame)
        control_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        # Кнопки управления
        btn_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        btn_frame.pack(pady=5)
        
        self.play_btn = ctk.CTkButton(btn_frame, text="▶ Воспр.", width=100, command=self.play)
        self.play_btn.pack(side="left", padx=5)
        
        self.pause_btn = ctk.CTkButton(btn_frame, text="⏸ Пауза", width=100, command=self.pause)
        self.pause_btn.pack(side="left", padx=5)
        
        self.stop_btn = ctk.CTkButton(btn_frame, text="⏹ Стоп", width=100, command=self.stop)
        self.stop_btn.pack(side="left", padx=5)
        
        self.next_btn = ctk.CTkButton(btn_frame, text="⏭ След.", width=100, command=self.next_file)
        self.next_btn.pack(side="left", padx=5)
        
        self.prev_btn = ctk.CTkButton(btn_frame, text="⏮ Пред.", width=100, command=self.prev_file)
        self.prev_btn.pack(side="left", padx=5)
        
        self.playlist_btn = ctk.CTkButton(btn_frame, text="▶ Плейлист", width=100, command=self.toggle_playlist)
        self.playlist_btn.pack(side="left", padx=5)
        
        self.fullscreen_btn = ctk.CTkButton(btn_frame, text="▶ Полный экран", width=120, command=self.toggle_fullscreen)
        self.fullscreen_btn.pack(side="left", padx=5)
        
        # Статус подключения
        self.connection_btn = ctk.CTkButton(
            control_frame, 
            text="Подключиться", 
            fg_color="gray",
            command=self.toggle_connection
        )
        self.connection_btn.pack(pady=5)
        
        # Основная область с двумя колонками
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Левая колонка - плейлист
        playlist_frame = ctk.CTkFrame(content_frame)
        playlist_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(playlist_frame, text="Плейлист", font=("Arial", 14)).pack(pady=5)
        
        # Treeview для плейлиста с полосой прокрутки
        self.playlist_tree = ttk.Treeview(
            playlist_frame,
            columns=('filename', 'path', 'duration', 'custom_duration'),
            show='headings',
            selectmode='browse'
        )
        self.playlist_tree.heading('filename', text='Имя файла')
        self.playlist_tree.heading('path', text='Путь')
        self.playlist_tree.heading('duration', text='Длительность')
        self.playlist_tree.heading('custom_duration', text='Время (сек)')
        self.playlist_tree.column('filename', width=150)
        self.playlist_tree.column('path', width=200)
        self.playlist_tree.column('duration', width=80)
        self.playlist_tree.column('custom_duration', width=80)
        
        scrollbar = ttk.Scrollbar(
            playlist_frame,
            orient="vertical",
            command=self.playlist_tree.yview
        )
        self.playlist_tree.configure(yscrollcommand=scrollbar.set)
        
        self.playlist_tree.pack(expand=True, fill="both", padx=5, pady=5, side="left")
        scrollbar.pack(fill="y", side="right")
        
        # Привязка события выбора
        self.playlist_tree.bind('<<TreeviewSelect>>', self.on_playlist_select)
        self.playlist_tree.bind('<Double-1>', self.edit_custom_duration)
        
        btn_frame_playlist = ctk.CTkFrame(playlist_frame, fg_color="transparent")
        btn_frame_playlist.pack(pady=5)
        
        ctk.CTkButton(
            btn_frame_playlist, 
            text="Добавить файлы", 
            command=self.add_files
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame_playlist, 
            text="Удалить выбранное", 
            command=self.remove_selected
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame_playlist, 
            text="Очистить плейлист", 
            command=self.clear_playlist
        ).pack(side="left", padx=5)
        
        # Правая колонка - управление и предпросмотр
        manage_frame = ctk.CTkFrame(content_frame)
        manage_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        # Предпросмотр
        ctk.CTkLabel(manage_frame, text="Предпросмотр", font=("Arial", 14)).pack(pady=5)
        
        self.preview_canvas = ctk.CTkCanvas(
            manage_frame, 
            width=400, 
            height=300,
            bg='gray20',
            highlightthickness=0
        )
        self.preview_canvas.pack(pady=5)
        
        # Информация о файле
        self.file_info = ctk.CTkLabel(manage_frame, text="Файл не выбран", text_color="gray")
        self.file_info.pack(pady=5)
        
        # Время воспроизведения
        self.time_label = ctk.CTkLabel(manage_frame, text="00:00 / 00:00", text_color="white")
        self.time_label.pack(pady=5)
        
        # Прогресс-бар для видео
        self.progress_bar = ttk.Progressbar(
            manage_frame,
            orient='horizontal',
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(pady=5)
        
        # Фрейм для установки времени
        duration_frame = ctk.CTkFrame(manage_frame, fg_color="transparent")
        duration_frame.pack(pady=5)
        
        ctk.CTkLabel(duration_frame, text="Время показа (сек):").pack(side="left", padx=5)
        
        self.duration_entry = ctk.CTkEntry(duration_frame, width=60)
        self.duration_entry.pack(side="left", padx=5)
        self.duration_entry.insert(0, "5")
        
        ctk.CTkButton(
            duration_frame, 
            text="Установить", 
            width=100,
            command=self.set_current_duration
        ).pack(side="left", padx=5)
        
        # Кнопки управления плейлистом
        ctk.CTkButton(
            manage_frame, 
            text="Сохранить плейлист", 
            command=self.save_playlist
        ).pack(pady=5, fill="x", padx=10)
        
        ctk.CTkButton(
            manage_frame, 
            text="Загрузить плейлист", 
            command=self.load_playlist
        ).pack(pady=5, fill="x", padx=10)
        
        ctk.CTkButton(
            manage_frame, 
            text="Отправить на дисплей", 
            command=self.send_to_display
        ).pack(pady=5, fill="x", padx=10)
        
        # Статус бар
        self.status_bar = ctk.CTkLabel(main_frame, text="Готов к работе", anchor="w")
        self.status_bar.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
    
    def update_playlist_display(self):
        self.playlist_tree.delete(*self.playlist_tree.get_children())
        for item in self.playlist:
            filename = os.path.basename(item['path'])
            duration = item.get('duration', 0)
            custom_duration = item.get('custom_duration', 0)
            
            duration_str = self.format_duration(duration)
            custom_duration_str = str(custom_duration) if custom_duration > 0 else ""
            
            self.playlist_tree.insert('', 'end', values=(
                filename, 
                item['path'], 
                duration_str,
                custom_duration_str
            ))
    
    def get_file_duration(self, file_path):
        """Возвращает длительность файла в секундах"""
        if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            try:
                cap = cv2.VideoCapture(file_path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    duration = frame_count / fps if fps > 0 else 0
                    cap.release()
                    return duration
            except:
                pass
        return 0  # Для изображений возвращаем 0
    
    def format_duration(self, seconds):
        """Форматирует длительность в формат MM:SS"""
        if seconds == 0:
            return "--:--"
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def add_files(self):
        filetypes = (
            ("Медиа файлы", "*.mp4 *.avi *.mov *.mkv *.jpg *.jpeg *.png"),
            ("Все файлы", "*.*")
        )
        
        files = filedialog.askopenfilenames(title="Выберите медиафайлы", filetypes=filetypes)
        if files:
            for file_path in files:
                duration = self.get_file_duration(file_path)
                self.playlist.append({
                    'path': file_path,
                    'duration': duration,
                    'custom_duration': 0  # По умолчанию 0 - использовать оригинальную длительность
                })
            
            self.update_playlist_display()
            self.status_bar.configure(text=f"Добавлено {len(files)} файлов в плейлист")
    
    def remove_selected(self):
        if not self.playlist:
            return
            
        selected_item = self.playlist_tree.selection()
        if selected_item:
            item = self.playlist_tree.item(selected_item)
            file_path = item['values'][1]
            
            # Находим и удаляем элемент из плейлиста
            for i, playlist_item in enumerate(self.playlist):
                if playlist_item['path'] == file_path:
                    del self.playlist[i]
                    break
            
            self.update_playlist_display()
            self.status_bar.configure(text="Файл удален из плейлиста")
                
            # Если удаляем текущий файл, останавливаем воспроизведение
            if self.current_file_index is not None and self.playlist and self.current_file_index >= len(self.playlist):
                self.stop()
    
    def clear_playlist(self):
        self.playlist = []
        self.update_playlist_display()
        self.stop()
        self.status_bar.configure(text="Плейлист очищен")
    
    def save_playlist(self):
        if not self.playlist:
            messagebox.showwarning("Ошибка", "Плейлист пуст")
            return
            
        file = filedialog.asksaveasfilename(
            title="Сохранить плейлист",
            defaultextension=".json",
            filetypes=(("JSON файлы", "*.json"),)
        )
        
        if file:
            try:
                with open(file, 'w') as f:
                    json.dump(self.playlist, f)
                self.status_bar.configure(text=f"Плейлист сохранен в {file}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить плейлист: {e}")
    
    def load_playlist(self):
        file = filedialog.askopenfilename(
            title="Загрузить плейлист",
            filetypes=(("JSON файлы", "*.json"),)
        )
        
        if file:
            try:
                with open(file, 'r') as f:
                    loaded_playlist = json.load(f)
                
                # Для совместимости с предыдущими версиями
                if isinstance(loaded_playlist[0], str):
                    self.playlist = [{'path': path, 'duration': self.get_file_duration(path), 'custom_duration': 0} 
                                   for path in loaded_playlist]
                else:
                    self.playlist = loaded_playlist
                
                self.update_playlist_display()
                self.status_bar.configure(text=f"Плейлист загружен из {file}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить плейлист: {e}")
    
    def on_playlist_select(self, event):
        selected_item = self.playlist_tree.selection()
        if selected_item:
            item = self.playlist_tree.item(selected_item)
            file_path = item['values'][1]
            self.show_preview(file_path)
    
    def edit_custom_duration(self, event):
        # Получаем выбранный элемент
        selected_item = self.playlist_tree.selection()
        if not selected_item:
            return
            
        column = self.playlist_tree.identify_column(event.x)
        if column != '#4':  # Только для колонки custom_duration
            return
            
        item = self.playlist_tree.item(selected_item)
        file_path = item['values'][1]
        
        # Находим элемент в плейлисте
        for i, playlist_item in enumerate(self.playlist):
            if playlist_item['path'] == file_path:
                # Создаем диалоговое окно для ввода времени
                dialog = ctk.CTkInputDialog(
                    text=f"Введите время показа для {os.path.basename(file_path)} (секунды):",
                    title="Установка времени"
                )
                try:
                    duration = int(dialog.get_input())
                    if duration >= 0:
                        self.playlist[i]['custom_duration'] = duration
                        self.update_playlist_display()
                except (ValueError, TypeError):
                    pass
                break
    
    def set_current_duration(self):
        selected_item = self.playlist_tree.selection()
        if not selected_item:
            messagebox.showwarning("Ошибка", "Выберите элемент из плейлиста")
            return
            
        try:
            duration = int(self.duration_entry.get())
            if duration < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Ошибка", "Введите положительное число секунд")
            return
            
        item = self.playlist_tree.item(selected_item)
        file_path = item['values'][1]
        
        # Находим и обновляем элемент в плейлисте
        for i, playlist_item in enumerate(self.playlist):
            if playlist_item['path'] == file_path:
                self.playlist[i]['custom_duration'] = duration
                self.update_playlist_display()
                self.status_bar.configure(text=f"Установлено время показа: {duration} сек")
                break
    
    def show_preview(self, file_path):
        self.stop_preview()
        
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            self.show_image_preview(file_path)
        elif file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            self.show_video_preview(file_path)
        
        # Обновляем информацию о файле
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # в MB
        
        # Находим элемент в плейлисте
        for item in self.playlist:
            if item['path'] == file_path:
                duration = item['duration']
                custom_duration = item['custom_duration']
                break
        
        duration_str = self.format_duration(duration)
        custom_duration_str = f"{custom_duration} сек" if custom_duration > 0 else "авто"
        
        self.file_info.configure(text=f"{filename}\nРазмер: {file_size:.2f} MB\nДлительность: {duration_str}\nВремя показа: {custom_duration_str}")
        self.time_label.configure(text=f"00:00 / {duration_str}")
    
    def show_image_preview(self, file_path):
        try:
            img = Image.open(file_path)
            img.thumbnail((400, 300))
            
            # Создаем изображение с серым фоном (для сохранения пропорций)
            bg = Image.new('RGB', (400, 300), (40, 40, 40))
            img = ImageOps.pad(img, (400, 300), color=(40, 40, 40))
            
            self.preview_image = ImageTk.PhotoImage(img)
            self.preview_canvas.create_image(0, 0, anchor='nw', image=self.preview_image)
        except Exception as e:
            self.preview_canvas.create_text(
                200, 150, 
                text=f"Ошибка загрузки\n{str(e)}", 
                fill="white",
                font=('Arial', 12)
            )
    
    def show_video_preview(self, file_path):
        self.video_capture = cv2.VideoCapture(file_path)
        if not self.video_capture.isOpened():
            self.preview_canvas.create_text(
                200, 150, 
                text="Ошибка загрузки видео", 
                fill="white",
                font=('Arial', 12)
            )
            return
        
        # Получаем информацию о видео
        fps = self.video_capture.get(cv2.CAP_PROP_FPS)
        frame_count = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        self.progress_bar['maximum'] = frame_count
        self.progress_bar['value'] = 0
        
        # Отображаем первый кадр
        ret, frame = self.video_capture.read()
        if ret:
            self.update_video_frame(frame)
    
    def update_video_frame(self, frame):
        if frame is None:
            return
            
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        img.thumbnail((400, 300))
        
        # Создаем изображение с серым фоном
        bg = Image.new('RGB', (400, 300), (40, 40, 40))
        img = ImageOps.pad(img, (400, 300), color=(40, 40, 40))
        
        self.preview_image = ImageTk.PhotoImage(img)
        self.preview_canvas.create_image(0, 0, anchor='nw', image=self.preview_image)
    
    def update_video_preview(self):
        if self.video_capture and self.playing_video:
            ret, frame = self.video_capture.read()
            if ret:
                self.update_video_frame(frame)
                current_frame = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
                self.progress_bar['value'] = current_frame
                
                # Обновляем время воспроизведения
                fps = self.video_capture.get(cv2.CAP_PROP_FPS)
                if fps > 0:
                    current_time = current_frame / fps
                    total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                    total_time = total_frames / fps
                    
                    current_str = self.format_duration(current_time)
                    total_str = self.format_duration(total_time)
                    self.time_label.configure(text=f"{current_str} / {total_str}")
                    
                    # Проверяем, не истекло ли установленное время
                    for item in self.playlist:
                        if item['path'] == self.playlist[self.current_file_index]['path']:
                            custom_duration = item['custom_duration']
                            if custom_duration > 0 and current_time >= custom_duration:
                                if self.playing_playlist:
                                    self.next_file()
                                else:
                                    self.stop()
                                return
            else:
                # Достигнут конец видео
                if self.playing_playlist:
                    self.next_file()
                else:
                    # Начинаем сначала
                    self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        self.after_id = self.after(30, self.update_video_preview)
    
    def stop_preview(self):
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
        self.playing_video = False
        self.progress_bar['value'] = 0
        self.time_label.configure(text="00:00 / 00:00")
    
    def play(self):
        if not self.playlist:
            messagebox.showwarning("Ошибка", "Плейлист пуст")
            return
            
        selected_item = self.playlist_tree.selection()
        if not selected_item and self.current_file_index is None:
            # Если ничего не выбрано, начинаем с первого файла
            self.current_file_index = 0
            self.playlist_tree.selection_set(self.playlist_tree.get_children()[0])
            selected_item = self.playlist_tree.selection()
        
        if selected_item:
            item = self.playlist_tree.item(selected_item)
            file_path = item['values'][1]
            
            # Находим индекс текущего файла
            for i, playlist_item in enumerate(self.playlist):
                if playlist_item['path'] == file_path:
                    self.current_file_index = i
                    break
            
            self.current_file_start_time = time.time()
            
            if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                self.playing_video = True
                self.show_video_preview(file_path)
                self.status_bar.configure(text=f"Воспроизведение видео: {os.path.basename(file_path)}")
                
                # Обновляем полноэкранное окно, если оно активно
                if self.fullscreen_playing:
                    self.update_fullscreen(file_path)
            else:
                self.status_bar.configure(text=f"Отображение фото: {os.path.basename(file_path)}")
                
                # Обновляем полноэкранное окно, если оно активно
                if self.fullscreen_playing:
                    self.update_fullscreen(file_path)
                
                # Для изображений запускаем таймер автоматического переключения
                if self.playing_playlist:
                    # Получаем установленное время или используем 5 сек по умолчанию
                    custom_duration = self.playlist[self.current_file_index].get('custom_duration', 0)
                    duration = custom_duration if custom_duration > 0 else 5
                    self.after(int(duration * 1000), self.next_file)
    
    def pause(self):
        self.playing_video = False
        self.status_bar.configure(text="Воспроизведение приостановлено")
        
        # Пауза в полноэкранном режиме
        if self.fullscreen_playing:
            self.playing_video = False
    
    def stop(self):
        self.stop_preview()
        self.playing_playlist = False
        self.current_file_index = None
        self.playlist_btn.configure(text="▶ Плейлист")
        self.status_bar.configure(text="Воспроизведение остановлено")
        
        # Остановка полноэкранного режима
        if self.fullscreen_playing:
            self.stop_fullscreen()
    
    def next_file(self):
        if not self.playlist:
            return
            
        if self.current_file_index is None:
            self.current_file_index = 0
        else:
            self.current_file_index = (self.current_file_index + 1) % len(self.playlist)
        
        next_item = self.playlist_tree.get_children()[self.current_file_index]
        self.playlist_tree.selection_set(next_item)
        self.playlist_tree.focus(next_item)
        
        # Обновляем полноэкранный режим, если он активен
        if self.fullscreen_playing:
            file_path = self.playlist[self.current_file_index]['path']
            self.update_fullscreen(file_path)
            
            # Для изображений устанавливаем таймер следующего файла
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg')) and self.playing_playlist:
                custom_duration = self.playlist[self.current_file_index].get('custom_duration', 0)
                duration = custom_duration if custom_duration > 0 else 5
                self.after(int(duration * 1000), self.next_file)
        else:
            self.play()
    
    def prev_file(self):
        if not self.playlist:
            return
            
        if self.current_file_index is None:
            self.current_file_index = 0
        else:
            self.current_file_index = (self.current_file_index - 1) % len(self.playlist)
        
        prev_item = self.playlist_tree.get_children()[self.current_file_index]
        self.playlist_tree.selection_set(prev_item)
        self.playlist_tree.focus(prev_item)
        self.play()
    
    def toggle_playlist(self):
        """Включить/выключить воспроизведение всего плейлиста"""
        if not self.playlist:
            messagebox.showwarning("Ошибка", "Плейлист пуст")
            return
            
        self.playing_playlist = not self.playing_playlist
        
        if self.playing_playlist:
            self.playlist_btn.configure(text="⏹ Стоп плейлист")
            if self.current_file_index is None:
                self.current_file_index = 0
                next_item = self.playlist_tree.get_children()[self.current_file_index]
                self.playlist_tree.selection_set(next_item)
                self.playlist_tree.focus(next_item)
            self.play()
        else:
            self.playlist_btn.configure(text="▶ Плейлист")
            self.status_bar.configure(text="Воспроизведение плейлиста остановлено")
    
    def toggle_fullscreen(self):
        """Включить/выключить полноэкранный режим воспроизведения"""
        if not self.playlist:
            messagebox.showwarning("Ошибка", "Плейлист пуст")
            return
            
        if self.fullscreen_playing:
            self.stop_fullscreen()
        else:
            # Если плейлист уже играет, продолжаем в полноэкранном режиме
            if self.playing_playlist:
                self.start_fullscreen()
            # Иначе начинаем воспроизведение текущего файла
            elif self.current_file_index is not None:
                self.start_fullscreen()
            # Если ничего не выбрано, начинаем с первого файла
            else:
                self.current_file_index = 0
                self.playlist_tree.selection_set(self.playlist_tree.get_children()[0])
                self.start_fullscreen()
    
    def start_fullscreen(self):
        """Запуск полноэкранного режима"""
        # Создаем полноэкранное окно
        self.fullscreen_window = ctk.CTkToplevel(self)
        self.fullscreen_window.attributes('-fullscreen', True)
        self.fullscreen_window.attributes('-topmost', True)
        
        # Добавляем кнопку выхода в углу экрана
        exit_btn = ctk.CTkButton(
            self.fullscreen_window,
            text="X",
            width=30,
            height=30,
            fg_color="red",
            command=self.stop_fullscreen
        )
        exit_btn.place(relx=0.98, rely=0.02, anchor="ne")
        
        # Получаем текущий файл
        file_path = self.playlist[self.current_file_index]['path']
        
        # Создаем холст для отображения
        screen_width = self.fullscreen_window.winfo_screenwidth()
        screen_height = self.fullscreen_window.winfo_screenheight()
        
        self.fullscreen_canvas = ctk.CTkCanvas(
            self.fullscreen_window,
            width=screen_width,
            height=screen_height,
            bg='black',
            highlightthickness=0
        )
        self.fullscreen_canvas.pack()
        
        # Обработчик закрытия окна
        self.fullscreen_window.protocol("WM_DELETE_WINDOW", self.stop_fullscreen)
        # Обработчик нажатия ESC для выхода
        self.fullscreen_window.bind('<Escape>', lambda e: self.stop_fullscreen())
        
        # Запускаем воспроизведение
        self.fullscreen_playing = True
        self.fullscreen_btn.configure(text="⏹ Выход из полного экрана")
        self.update_fullscreen(file_path)
        
        # Если это изображение и включен плейлист, устанавливаем таймер
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')) and self.playing_playlist:
            custom_duration = self.playlist[self.current_file_index].get('custom_duration', 0)
            duration = custom_duration if custom_duration > 0 else 5
            self.after(int(duration * 1000), self.next_file)
    
    def update_fullscreen(self, file_path):
        """Обновление содержимого полноэкранного окна"""
        if not self.fullscreen_playing or not self.fullscreen_window:
            return
        
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            # Отображаем изображение
            try:
                img = Image.open(file_path)
                screen_width = self.fullscreen_window.winfo_screenwidth()
                screen_height = self.fullscreen_window.winfo_screenheight()
                
                # Масштабируем с сохранением пропорций
                img.thumbnail((screen_width, screen_height))
                
                # Центрируем изображение
                x = (screen_width - img.width) // 2
                y = (screen_height - img.height) // 2
                
                self.fullscreen_image = ImageTk.PhotoImage(img)
                self.fullscreen_canvas.create_image(x, y, anchor='nw', image=self.fullscreen_image)
            except Exception as e:
                self.fullscreen_canvas.create_text(
                    screen_width // 2, screen_height // 2, 
                    text=f"Ошибка загрузки\n{str(e)}", 
                    fill="white",
                    font=('Arial', 24)
                )
        elif file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            # Отображаем видео
            if not hasattr(self, 'fullscreen_capture') or not self.fullscreen_capture:
                self.fullscreen_capture = cv2.VideoCapture(file_path)
            
            if self.playing_video:
                ret, frame = self.fullscreen_capture.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame)
                    
                    screen_width = self.fullscreen_window.winfo_screenwidth()
                    screen_height = self.fullscreen_window.winfo_screenheight()
                    
                    # Масштабируем с сохранением пропорций
                    img.thumbnail((screen_width, screen_height))
                    
                    # Центрируем изображение
                    x = (screen_width - img.width) // 2
                    y = (screen_height - img.height) // 2
                    
                    self.fullscreen_image = ImageTk.PhotoImage(img)
                    self.fullscreen_canvas.create_image(x, y, anchor='nw', image=self.fullscreen_image)
                else:
                    # Достигнут конец видео
                    if self.playing_playlist:
                        self.next_file()
                    else:
                        # Начинаем сначала
                        self.fullscreen_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        # Планируем следующее обновление
        if self.fullscreen_playing:
            self.after(30, lambda: self.update_fullscreen(file_path))
    
    def stop_fullscreen(self):
        """Остановка полноэкранного режима"""
        if hasattr(self, 'fullscreen_capture') and self.fullscreen_capture:
            self.fullscreen_capture.release()
            self.fullscreen_capture = None
        
        if self.fullscreen_window:
            self.fullscreen_window.destroy()
            self.fullscreen_window = None
        
        self.fullscreen_playing = False
        self.fullscreen_btn.configure(text="▶ Полный экран")
        
        # Если был режим плейлиста, продолжаем воспроизведение в основном окне
        if self.playing_playlist and self.current_file_index is not None:
            file_path = self.playlist[self.current_file_index]['path']
            self.show_preview(file_path)
            if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                self.playing_video = True
    
    def toggle_connection(self):
        self.connected = not self.connected
        if self.connected:
            self.connection_btn.configure(text="Отключиться", fg_color="green")
            self.status_bar.configure(text="Подключено к дисплею")
        else:
            self.connection_btn.configure(text="Подключиться", fg_color="gray")
            self.status_bar.configure(text="Отключено от дисплея")
    
    def send_to_display(self):
        if not self.connected:
            messagebox.showwarning("Ошибка", "Сначала подключитесь к дисплею")
            return
            
        if not self.playlist:
            messagebox.showwarning("Ошибка", "Плейлист пуст")
            return
            
        # Здесь будет реальная логика отправки на дисплей
        self.status_bar.configure(text="Плейлист отправлен на дисплей")
    
    def __del__(self):
        self.stop_preview()
        self.stop_fullscreen()
        if self.after_id:
            self.after_cancel(self.after_id)

if __name__ == "__main__":
    app = MediaControlApp()
    app.mainloop() 