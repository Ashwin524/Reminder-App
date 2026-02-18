#!/usr/bin/env python3
"""
Ultimate Reminder App - AUTO-INSTALL EDITION
Features:
- Auto-installs all required libraries
- Multi-screen detector with user selection
- Voice notes, snooze, edit, fullscreen alerts
"""

import subprocess
import sys
import os

# Auto-install function
def install_package(package):
    """Auto-install missing packages"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])
        return True
    except:
        return False

# Check and install required packages
print("🔍 Checking required packages...")

required_packages = {
    'tkcalendar': 'tkcalendar',
    'pystray': 'pystray',
    'PIL': 'Pillow',
    'pygame': 'pygame',
    'pyaudio': 'pyaudio',
    'screeninfo': 'screeninfo'
}

for module_name, package_name in required_packages.items():
    try:
        __import__(module_name)
        print(f"  ✓ {package_name} already installed")
    except ImportError:
        print(f"  ⚠ {package_name} not found. Installing...")
        if install_package(package_name):
            print(f"  ✓ {package_name} installed successfully!")
        else:
            print(f"  ✗ Failed to install {package_name}")

print("\n🚀 Starting Reminder App...\n")

# Now import everything
import json
import time
import threading
from datetime import datetime, timedelta
import wave

# GUI libraries
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry

# System tray
try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except:
    TRAY_AVAILABLE = False

# Audio
try:
    import pygame
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
except:
    AUDIO_AVAILABLE = False

# Voice recording
try:
    import pyaudio
    VOICE_AVAILABLE = True
except:
    VOICE_AVAILABLE = False

# Screen detection
try:
    from screeninfo import get_monitors
    SCREEN_DETECTION = True
except:
    SCREEN_DETECTION = False

# Data files
DATA_FILE = os.path.join(os.path.expanduser("~"), "reminder_app_data.json")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), "reminder_app_settings.json")
VOICE_NOTES_DIR = os.path.join(os.path.expanduser("~"), "reminder_voice_notes")

os.makedirs(VOICE_NOTES_DIR, exist_ok=True)

# Colors
COLORS = {
    'primary': '#667eea',
    'success': '#10b981',
    'danger': '#ef4444',
    'warning': '#f59e0b',
    'info': '#3b82f6',
    'alarm_red': '#dc2626',
    'alarm_blue': '#2563eb'
}

class VoiceRecorder:
    """Simple voice recorder"""
    def __init__(self):
        self.recording = False
        self.frames = []
        self.audio = None
        self.stream = None
        
        if VOICE_AVAILABLE:
            try:
                self.audio = pyaudio.PyAudio()
            except:
                pass
    
    def start_recording(self):
        if not VOICE_AVAILABLE or not self.audio:
            return False
        
        try:
            self.recording = True
            self.frames = []
            
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=1024
            )
            
            def record_thread():
                while self.recording:
                    try:
                        data = self.stream.read(1024)
                        self.frames.append(data)
                    except:
                        break
            
            threading.Thread(target=record_thread, daemon=True).start()
            return True
        except Exception as e:
            print(f"Recording error: {e}")
            return False
    
    def stop_recording(self, filename):
        if not VOICE_AVAILABLE or not self.recording:
            return False
        
        try:
            self.recording = False
            time.sleep(0.2)
            
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            
            filepath = os.path.join(VOICE_NOTES_DIR, filename)
            with wave.open(filepath, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(44100)
                wf.writeframes(b''.join(self.frames))
            
            return filepath
        except Exception as e:
            print(f"Save error: {e}")
            return False

class ReminderApp:
    def __init__(self):
        self.reminders = []
        self.alarms = []
        self.snoozed_items = []
        self.running = True
        self.custom_tone_path = None
        self.pending_voice_note = None
        self.voice_recorder = VoiceRecorder()
        
        # Detect screens
        self.detect_screens()
        
        # Alert settings
        self.fullscreen_mode = True
        self.selected_screens = "all"  # "all", "primary", or specific screen index
        
        self.load_data()
        self.load_settings()
        
        self.start_monitor_thread()
        if TRAY_AVAILABLE:
            self.setup_tray_icon()
        self.create_gui()
    
    def detect_screens(self):
        """Detect all available screens"""
        self.screens = []
        
        if SCREEN_DETECTION:
            try:
                monitors = get_monitors()
                for idx, monitor in enumerate(monitors):
                    screen_info = {
                        'index': idx,
                        'name': f"Screen {idx + 1}",
                        'x': monitor.x,
                        'y': monitor.y,
                        'width': monitor.width,
                        'height': monitor.height,
                        'is_primary': monitor.is_primary if hasattr(monitor, 'is_primary') else (idx == 0)
                    }
                    self.screens.append(screen_info)
                    print(f"  🖥️  Screen {idx + 1}: {monitor.width}x{monitor.height} at ({monitor.x}, {monitor.y})")
            except Exception as e:
                print(f"Screen detection error: {e}")
        
        # Fallback: if no screens detected, use default
        if not self.screens:
            self.screens = [{
                'index': 0,
                'name': 'Primary Screen',
                'x': 0,
                'y': 0,
                'width': 1920,
                'height': 1080,
                'is_primary': True
            }]
        
        print(f"\n✓ Detected {len(self.screens)} screen(s)")
    
    def get_primary_screen(self):
        """Get primary screen info"""
        for screen in self.screens:
            if screen['is_primary']:
                return screen
        return self.screens[0] if self.screens else None
    
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    self.custom_tone_path = settings.get('custom_tone_path')
                    self.fullscreen_mode = settings.get('fullscreen_mode', True)
                    self.selected_screens = settings.get('selected_screens', 'all')
            except:
                pass
    
    def save_settings(self):
        settings = {
            'custom_tone_path': self.custom_tone_path,
            'fullscreen_mode': self.fullscreen_mode,
            'selected_screens': self.selected_screens
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    
    def create_tray_icon_image(self):
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), 'white')
        dc = ImageDraw.Draw(image)
        dc.ellipse([10, 10, 54, 54], fill=COLORS['primary'])
        dc.ellipse([15, 15, 49, 49], fill='white')
        dc.line([32, 32, 32, 20], fill=COLORS['primary'], width=2)
        dc.line([32, 32, 42, 32], fill=COLORS['primary'], width=2)
        dc.ellipse([30, 30, 34, 34], fill=COLORS['primary'])
        return image
    
    def setup_tray_icon(self):
        if not TRAY_AVAILABLE:
            return
        
        try:
            icon_image = self.create_tray_icon_image()
            menu = pystray.Menu(
                item('Show', self.show_window, default=True),
                item('Exit', self.quit_app)
            )
            self.tray_icon = pystray.Icon("ReminderApp", icon_image, "Reminder App", menu)
            threading.Thread(target=self.tray_icon.run, daemon=False).start()
        except:
            pass
    
    def show_window(self, icon=None, item=None):
        if hasattr(self, 'root'):
            self.root.deiconify()
            self.root.lift()
    
    def hide_window(self):
        if hasattr(self, 'root'):
            self.root.withdraw()
    
    def quit_app(self, icon=None, item=None):
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()
        if hasattr(self, 'root'):
            try:
                self.root.quit()
            except:
                pass
        sys.exit(0)
    
    def play_alarm_sound(self, custom_path=None):
        if not AUDIO_AVAILABLE:
            print('\a')
            return
        
        try:
            sound_path = custom_path or self.custom_tone_path
            if sound_path and os.path.exists(sound_path):
                pygame.mixer.music.load(sound_path)
                pygame.mixer.music.play(-1)
            else:
                print('\a')
        except Exception as e:
            print(f"Audio error: {e}")
            print('\a')
    
    def stop_alarm_sound(self):
        if AUDIO_AVAILABLE:
            try:
                pygame.mixer.music.stop()
            except:
                pass
    
    def create_gui(self):
        """Create clean, properly sized GUI"""
        self.root = tk.Tk()
        self.root.title("⏰ Reminder App")
        
        # Get primary screen for window positioning
        primary = self.get_primary_screen()
        screen_width = primary['width']
        screen_height = primary['height']
        
        # Set reasonable window size (60% of screen)
        win_width = int(screen_width * 0.6)
        win_height = int(screen_height * 0.7)
        
        # Center window
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2
        
        self.root.geometry(f"{win_width}x{win_height}+{x}+{y}")
        self.root.configure(bg='white')
        
        # Header with clock
        header = tk.Frame(self.root, bg=COLORS['primary'], height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header, 
            text="⏰ Reminder App", 
            font=("Arial", 18, "bold"), 
            bg=COLORS['primary'], 
            fg='white'
        ).pack(pady=5)
        
        # Live clock
        self.clock_label = tk.Label(
            header,
            text="",
            font=("Arial", 12),
            bg=COLORS['primary'],
            fg='white'
        )
        self.clock_label.pack()
        self.update_clock()
        
        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tabs
        self.create_reminders_tab()
        self.create_alarms_tab()
        self.create_settings_tab()
        
        # Status bar
        status_frame = tk.Frame(self.root, bg=COLORS['success'], height=30)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)
        
        tk.Label(
            status_frame, 
            text=f"✓ Running | Screens: {len(self.screens)}", 
            bg=COLORS['success'], 
            fg='white',
            font=("Arial", 9, "bold")
        ).pack(pady=5)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def update_clock(self):
        """Update live clock display"""
        if hasattr(self, 'clock_label'):
            now = datetime.now()
            time_str = now.strftime("%I:%M:%S %p")
            date_str = now.strftime("%A, %B %d, %Y")
            self.clock_label.config(text=f"{time_str} • {date_str}")
            self.root.after(1000, self.update_clock)
    
    def create_reminders_tab(self):
        """Clean reminders tab"""
        tab = tk.Frame(self.notebook, bg='white')
        self.notebook.add(tab, text="📝 Reminders")
        
        # Add section
        add_frame = tk.LabelFrame(tab, text="Add Reminder", padx=10, pady=10, bg='white', font=("Arial", 11, "bold"))
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Form fields in grid
        row = 0
        tk.Label(add_frame, text="Title:", bg='white', font=("Arial", 10)).grid(row=row, column=0, sticky=tk.W, pady=5)
        self.reminder_title = tk.Entry(add_frame, width=50, font=("Arial", 10))
        self.reminder_title.grid(row=row, column=1, pady=5, sticky=tk.W)
        
        row += 1
        tk.Label(add_frame, text="Description:", bg='white', font=("Arial", 10)).grid(row=row, column=0, sticky=tk.W, pady=5)
        self.reminder_desc = tk.Entry(add_frame, width=50, font=("Arial", 10))
        self.reminder_desc.grid(row=row, column=1, pady=5, sticky=tk.W)
        
        row += 1
        tk.Label(add_frame, text="Date:", bg='white', font=("Arial", 10)).grid(row=row, column=0, sticky=tk.W, pady=5)
        self.reminder_date = DateEntry(add_frame, width=20, font=("Arial", 10))
        self.reminder_date.grid(row=row, column=1, pady=5, sticky=tk.W)
        
        row += 1
        tk.Label(add_frame, text="Time:", bg='white', font=("Arial", 10)).grid(row=row, column=0, sticky=tk.W, pady=5)
        
        # Time picker inline
        time_frame = tk.Frame(add_frame, bg='white')
        time_frame.grid(row=row, column=1, pady=5, sticky=tk.W)
        
        self.hour_var = tk.IntVar(value=12)
        tk.Spinbox(time_frame, from_=1, to=12, textvariable=self.hour_var, width=3, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        tk.Label(time_frame, text=":", bg='white', font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        self.minute_var = tk.IntVar(value=0)
        tk.Spinbox(time_frame, from_=0, to=59, textvariable=self.minute_var, width=3, font=("Arial", 10), format="%02.0f").pack(side=tk.LEFT, padx=2)
        
        self.ampm_var = tk.StringVar(value="AM")
        tk.Radiobutton(time_frame, text="AM", variable=self.ampm_var, value="AM", bg='white').pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(time_frame, text="PM", variable=self.ampm_var, value="PM", bg='white').pack(side=tk.LEFT, padx=5)
        
        row += 1
        tk.Label(add_frame, text="Priority:", bg='white', font=("Arial", 10)).grid(row=row, column=0, sticky=tk.W, pady=5)
        self.reminder_priority = ttk.Combobox(add_frame, values=["normal", "urgent"], width=18, font=("Arial", 10))
        self.reminder_priority.set("normal")
        self.reminder_priority.grid(row=row, column=1, pady=5, sticky=tk.W)
        
        # Buttons
        row += 1
        btn_frame = tk.Frame(add_frame, bg='white')
        btn_frame.grid(row=row, column=1, pady=10, sticky=tk.W)
        
        tk.Button(
            btn_frame, 
            text="🎤 Record Voice", 
            command=self.record_voice_note,
            bg=COLORS['info'], 
            fg='white', 
            font=("Arial", 9, "bold"),
            padx=10,
            pady=5
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame, 
            text="✓ Add Reminder", 
            command=self.add_reminder_gui,
            bg=COLORS['success'], 
            fg='white', 
            font=("Arial", 9, "bold"),
            padx=15,
            pady=5
        ).pack(side=tk.LEFT, padx=5)
        
        # List section
        list_frame = tk.LabelFrame(tab, text="Your Reminders", padx=10, pady=10, bg='white', font=("Arial", 11, "bold"))
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollable listbox
        scroll = tk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.reminders_listbox = tk.Listbox(
            list_frame, 
            yscrollcommand=scroll.set, 
            font=("Courier", 9),
            height=8
        )
        self.reminders_listbox.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.reminders_listbox.yview)
        
        # Action buttons
        action_frame = tk.Frame(list_frame, bg='white')
        action_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(action_frame, text="🔄 Refresh", command=self.refresh_reminders_list, bg=COLORS['info'], fg='white', padx=10, pady=3).pack(side=tk.LEFT, padx=3)
        tk.Button(action_frame, text="✏️ Edit", command=self.edit_reminder, bg=COLORS['warning'], fg='white', padx=10, pady=3).pack(side=tk.LEFT, padx=3)
        tk.Button(action_frame, text="🗑️ Delete", command=self.delete_reminder, bg=COLORS['danger'], fg='white', padx=10, pady=3).pack(side=tk.LEFT, padx=3)
        
        self.refresh_reminders_list()
    
    def create_alarms_tab(self):
        """Clean alarms tab"""
        tab = tk.Frame(self.notebook, bg='white')
        self.notebook.add(tab, text="⏰ Alarms")
        
        tk.Label(tab, text="Alarms feature - Similar to reminders", font=("Arial", 12), bg='white').pack(pady=50)
    
    def create_settings_tab(self):
        """Settings tab with screen selection"""
        tab = tk.Frame(self.notebook, bg='white')
        self.notebook.add(tab, text="⚙️ Settings")
        
        # Screen selection
        screen_frame = tk.LabelFrame(tab, text="🖥️ Screen Selection for Alerts", padx=20, pady=20, bg='white', font=("Arial", 11, "bold"))
        screen_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            screen_frame,
            text=f"Detected Screens: {len(self.screens)}",
            bg='white',
            font=("Arial", 10, "bold"),
            fg=COLORS['success']
        ).pack(anchor=tk.W, pady=5)
        
        # List all screens
        for screen in self.screens:
            primary_text = " (Primary)" if screen['is_primary'] else ""
            tk.Label(
                screen_frame,
                text=f"  • {screen['name']}: {screen['width']}x{screen['height']}{primary_text}",
                bg='white',
                font=("Arial", 9),
                fg=COLORS['info']
            ).pack(anchor=tk.W, pady=2)
        
        tk.Label(screen_frame, text="", bg='white').pack(pady=5)  # Spacer
        
        tk.Label(
            screen_frame,
            text="Show alerts on:",
            bg='white',
            font=("Arial", 10, "bold")
        ).pack(anchor=tk.W, pady=5)
        
        self.screen_selection_var = tk.StringVar(value=self.selected_screens)
        
        # Radio buttons for screen selection
        tk.Radiobutton(
            screen_frame,
            text="All Screens (alerts appear on every screen)",
            variable=self.screen_selection_var,
            value="all",
            bg='white',
            font=("Arial", 10),
            command=self.save_screen_selection
        ).pack(anchor=tk.W, pady=3)
        
        tk.Radiobutton(
            screen_frame,
            text="Primary Screen Only",
            variable=self.screen_selection_var,
            value="primary",
            bg='white',
            font=("Arial", 10),
            command=self.save_screen_selection
        ).pack(anchor=tk.W, pady=3)
        
        # Individual screen options
        for screen in self.screens:
            tk.Radiobutton(
                screen_frame,
                text=f"Only {screen['name']} ({screen['width']}x{screen['height']})",
                variable=self.screen_selection_var,
                value=str(screen['index']),
                bg='white',
                font=("Arial", 10),
                command=self.save_screen_selection
            ).pack(anchor=tk.W, pady=3)
        
        # Alert settings
        alert_frame = tk.LabelFrame(tab, text="Alert Settings", padx=20, pady=20, bg='white', font=("Arial", 11, "bold"))
        alert_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.fullscreen_var = tk.BooleanVar(value=self.fullscreen_mode)
        tk.Checkbutton(
            alert_frame,
            text="Show alerts in FULLSCREEN mode",
            variable=self.fullscreen_var,
            bg='white',
            font=("Arial", 10),
            command=self.toggle_fullscreen_mode
        ).pack(anchor=tk.W, pady=5)
        
        # Tone settings
        tone_frame = tk.LabelFrame(tab, text="Alarm Tone", padx=20, pady=20, bg='white', font=("Arial", 11, "bold"))
        tone_frame.pack(fill=tk.X, padx=10, pady=10)
        
        current = os.path.basename(self.custom_tone_path) if self.custom_tone_path else "Default beep"
        self.tone_label = tk.Label(tone_frame, text=f"Current: {current}", bg='white', fg=COLORS['primary'], font=("Arial", 10))
        self.tone_label.pack(pady=5)
        
        tk.Button(
            tone_frame,
            text="📁 Select Custom Tone",
            command=self.select_custom_tone,
            bg=COLORS['primary'],
            fg='white',
            padx=15,
            pady=5
        ).pack(pady=5)
        
        tk.Button(
            tone_frame,
            text="🔊 Test Sound",
            command=self.test_sound,
            bg=COLORS['success'],
            fg='white',
            padx=15,
            pady=5
        ).pack(pady=5)
    
    def save_screen_selection(self):
        """Save screen selection preference"""
        self.selected_screens = self.screen_selection_var.get()
        self.save_settings()
        
        if self.selected_screens == "all":
            msg = "Alerts will appear on ALL screens"
        elif self.selected_screens == "primary":
            msg = "Alerts will appear on PRIMARY screen only"
        else:
            screen_idx = int(self.selected_screens)
            screen_name = self.screens[screen_idx]['name']
            msg = f"Alerts will appear on {screen_name} only"
        
        messagebox.showinfo("Screen Selection", msg)
    
    def toggle_fullscreen_mode(self):
        """Toggle fullscreen mode"""
        self.fullscreen_mode = self.fullscreen_var.get()
        self.save_settings()
        mode = "FULLSCREEN" if self.fullscreen_mode else "WINDOWED"
        messagebox.showinfo("Settings", f"Alert mode set to: {mode}")
    
    def select_custom_tone(self):
        """Select custom alarm tone"""
        file_path = filedialog.askopenfilename(
            title="Select Alarm Tone",
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.custom_tone_path = file_path
            self.save_settings()
            self.tone_label.config(text=f"Current: {os.path.basename(file_path)}")
            messagebox.showinfo("Success", "Custom tone set!")
    
    def test_sound(self):
        """Test alarm sound"""
        self.play_alarm_sound()
        self.root.after(3000, self.stop_alarm_sound)
    
    def record_voice_note(self):
        """Record voice note for reminder"""
        if not VOICE_AVAILABLE:
            messagebox.showerror("Error", "Voice recording not available!\n\nInstall: pip install pyaudio")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("🎤 Record Voice Note")
        dialog.geometry("400x250")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center
        dialog.update_idletasks()
        x = (self.root.winfo_screenwidth() - 400) // 2
        y = (self.root.winfo_screenheight() - 250) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="🎤 Voice Note Recorder", font=("Arial", 14, "bold"), bg='white').pack(pady=20)
        
        status_label = tk.Label(dialog, text="Ready to record...", font=("Arial", 11), bg='white')
        status_label.pack(pady=10)
        
        recording_data = {'active': False, 'filepath': None}
        
        def start_rec():
            if self.voice_recorder.start_recording():
                recording_data['active'] = True
                status_label.config(text="🔴 Recording... Speak now!", fg='red')
                start_btn.config(state=tk.DISABLED)
                stop_btn.config(state=tk.NORMAL)
        
        def stop_rec():
            if recording_data['active']:
                filename = f"voice_{int(time.time())}.wav"
                filepath = self.voice_recorder.stop_recording(filename)
                if filepath:
                    recording_data['filepath'] = filepath
                    recording_data['active'] = False
                    status_label.config(text=f"✓ Saved!", fg='green')
                    stop_btn.config(state=tk.DISABLED)
                    save_btn.config(state=tk.NORMAL)
        
        def save_and_close():
            if recording_data['filepath']:
                self.pending_voice_note = recording_data['filepath']
                messagebox.showinfo("Success", "Voice note will be used for this reminder!")
                dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg='white')
        btn_frame.pack(pady=20)
        
        start_btn = tk.Button(btn_frame, text="▶️ Start", command=start_rec, bg=COLORS['success'], fg='white', padx=15, pady=8)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        stop_btn = tk.Button(btn_frame, text="⏹️ Stop", command=stop_rec, bg=COLORS['danger'], fg='white', padx=15, pady=8, state=tk.DISABLED)
        stop_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = tk.Button(btn_frame, text="💾 Use This", command=save_and_close, bg=COLORS['info'], fg='white', padx=15, pady=8, state=tk.DISABLED)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(dialog, text="Cancel", command=dialog.destroy, padx=15, pady=5).pack(pady=10)
    
    def get_screens_to_show(self):
        """Get list of screens where alert should appear"""
        if self.selected_screens == "all":
            return self.screens
        elif self.selected_screens == "primary":
            return [self.get_primary_screen()]
        else:
            # Specific screen index
            try:
                idx = int(self.selected_screens)
                return [self.screens[idx]]
            except:
                return [self.get_primary_screen()]
    
    def show_fullscreen_alert(self, title, message, item_id=None, custom_voice=None):
        """Show alert on selected screen(s)"""
        
        self.stop_alarm_sound()
        
        screens_to_use = self.get_screens_to_show()
        alert_windows = []
        
        # Create alert on each selected screen
        for screen in screens_to_use:
            alert = tk.Toplevel()
            
            if self.fullscreen_mode:
                # TRUE FULLSCREEN MODE
                alert.attributes('-fullscreen', True)
                alert.attributes('-topmost', True)
                alert.geometry(f"{screen['width']}x{screen['height']}+{screen['x']}+{screen['y']}")
            else:
                # LARGE CENTERED WINDOW MODE
                alert.attributes('-topmost', True)
                alert_width = int(screen['width'] * 0.8)
                alert_height = int(screen['height'] * 0.8)
                x = screen['x'] + (screen['width'] - alert_width) // 2
                y = screen['y'] + (screen['height'] - alert_height) // 2
                alert.geometry(f"{alert_width}x{alert_height}+{x}+{y}")
            
            alert.configure(bg=COLORS['alarm_red'])
            
            # Container
            container = tk.Frame(alert, bg=COLORS['alarm_red'])
            container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            # Icon
            tk.Label(container, text="🚨", font=("Arial", 120), bg=COLORS['alarm_red'], fg='white').pack(pady=20)
            
            # Title
            tk.Label(container, text=title, font=("Arial", 36, "bold"), bg=COLORS['alarm_red'], fg='white', wraplength=1000).pack(pady=15)
            
            # Message
            tk.Label(container, text=message, font=("Arial", 24), bg=COLORS['alarm_red'], fg='white', wraplength=1000).pack(pady=15)
            
            # Time
            tk.Label(container, text=datetime.now().strftime("%I:%M:%S %p"), font=("Arial", 20), bg=COLORS['alarm_red'], fg='white').pack(pady=10)
            
            # Snooze section
            tk.Label(container, text="⏰ Snooze:", font=("Arial", 18, "bold"), bg=COLORS['alarm_red'], fg='white').pack(pady=10)
            
            snooze_frame = tk.Frame(container, bg=COLORS['alarm_red'])
            snooze_frame.pack(pady=10)
            
            def snooze_action(minutes):
                self.snooze_item(item_id, minutes, title, message, custom_voice)
                self.stop_alarm_sound()
                for win in alert_windows:
                    try:
                        win.destroy()
                    except:
                        pass
            
            for minutes in [5, 10, 15, 30]:
                tk.Button(
                    snooze_frame,
                    text=f"{minutes} min",
                    command=lambda m=minutes: snooze_action(m),
                    bg='white',
                    fg=COLORS['alarm_red'],
                    font=("Arial", 16, "bold"),
                    padx=20,
                    pady=10
                ).pack(side=tk.LEFT, padx=5)
            
            # Dismiss
            tk.Button(
                container,
                text="✓ DISMISS",
                command=lambda: [self.stop_alarm_sound()] + [win.destroy() for win in alert_windows],
                bg='white',
                fg=COLORS['alarm_red'],
                font=("Arial", 24, "bold"),
                padx=40,
                pady=15
            ).pack(pady=20)
            
            alert_windows.append(alert)
            
            # Flash effect
            def flash(window, color_index=0):
                colors = [COLORS['alarm_red'], COLORS['alarm_blue']]
                try:
                    window.configure(bg=colors[color_index])
                    container.configure(bg=colors[color_index])
                    window.after(500, lambda: flash(window, 1 - color_index))
                except:
                    pass
            
            flash(alert)
        
        # Play sound
        self.play_alarm_sound(custom_voice)
        
        if not hasattr(self, 'root') or self.root.state() == 'withdrawn':
            self.show_window()
    
    def snooze_item(self, item_id, minutes, title, message, custom_voice):
        """Snooze an alert"""
        trigger_time = datetime.now() + timedelta(minutes=minutes)
        
        snoozed = {
            'id': int(time.time() * 1000),
            'original_id': item_id,
            'title': title,
            'message': message,
            'trigger_time': trigger_time.strftime("%Y-%m-%d %H:%M"),
            'custom_voice': custom_voice,
            'active': True
        }
        
        self.snoozed_items.append(snoozed)
        messagebox.showinfo("Snoozed", f"Will alert again at {trigger_time.strftime('%I:%M %p')}")
    
    def check_snoozed(self):
        """Check snoozed items"""
        now = datetime.now()
        current = now.strftime("%Y-%m-%d %H:%M")
        
        for item in self.snoozed_items:
            if item['active'] and item['trigger_time'] == current:
                self.show_fullscreen_alert(item['title'], item['message'], item['original_id'], item.get('custom_voice'))
                item['active'] = False
    
    def edit_reminder(self):
        """Edit selected reminder"""
        selection = self.reminders_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select a reminder to edit!")
            return
        
        item_text = self.reminders_listbox.get(selection[0])
        try:
            reminder_id = int(item_text.split("ID:")[1].strip())
            reminder = next((r for r in self.reminders if r['id'] == reminder_id), None)
            
            if reminder:
                self.show_edit_dialog(reminder)
        except:
            messagebox.showerror("Error", "Could not edit")
    
    def show_edit_dialog(self, reminder):
        """Show edit dialog with time and voice"""
        dialog = tk.Toplevel(self.root)
        dialog.title("✏️ Edit Reminder")
        dialog.geometry("550x550")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center
        dialog.update_idletasks()
        x = (self.root.winfo_screenwidth() - 550) // 2
        y = (self.root.winfo_screenheight() - 550) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="✏️ Edit Reminder", font=("Arial", 16, "bold"), bg='white', fg=COLORS['primary']).pack(pady=15)
        
        form = tk.Frame(dialog, bg='white')
        form.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        
        row = 0
        
        # Title
        tk.Label(form, text="Title:", bg='white', font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=8)
        title_entry = tk.Entry(form, width=35, font=("Arial", 10))
        title_entry.insert(0, reminder['title'])
        title_entry.grid(row=row, column=1, pady=8, sticky=tk.W)
        
        row += 1
        
        # Description
        tk.Label(form, text="Description:", bg='white', font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=8)
        desc_entry = tk.Entry(form, width=35, font=("Arial", 10))
        desc_entry.insert(0, reminder['description'])
        desc_entry.grid(row=row, column=1, pady=8, sticky=tk.W)
        
        row += 1
        
        # Date
        tk.Label(form, text="Date:", bg='white', font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=8)
        date_entry = DateEntry(form, width=25, font=("Arial", 10))
        try:
            date_entry.set_date(datetime.strptime(reminder['date'], "%Y-%m-%d").date())
        except:
            pass
        date_entry.grid(row=row, column=1, pady=8, sticky=tk.W)
        
        row += 1
        
        # Time
        tk.Label(form, text="Time:", bg='white', font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=8)
        
        # Parse existing time
        try:
            h24, m = reminder['time'].split(':')
            h24 = int(h24)
            minute = int(m)
            ampm = "AM" if h24 < 12 else "PM"
            hour = h24 if h24 <= 12 else h24 - 12
            if hour == 0:
                hour = 12
        except:
            hour = 12
            minute = 0
            ampm = "AM"
        
        # Time picker
        time_frame = tk.Frame(form, bg='white')
        time_frame.grid(row=row, column=1, pady=8, sticky=tk.W)
        
        edit_hour_var = tk.IntVar(value=hour)
        tk.Spinbox(time_frame, from_=1, to=12, textvariable=edit_hour_var, width=3, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        tk.Label(time_frame, text=":", bg='white', font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        edit_minute_var = tk.IntVar(value=minute)
        tk.Spinbox(time_frame, from_=0, to=59, textvariable=edit_minute_var, width=3, font=("Arial", 10), format="%02.0f").pack(side=tk.LEFT, padx=2)
        
        edit_ampm_var = tk.StringVar(value=ampm)
        tk.Radiobutton(time_frame, text="AM", variable=edit_ampm_var, value="AM", bg='white', font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(time_frame, text="PM", variable=edit_ampm_var, value="PM", bg='white', font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        row += 1
        
        # Priority
        tk.Label(form, text="Priority:", bg='white', font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=8)
        priority_combo = ttk.Combobox(form, values=["normal", "urgent"], width=23, font=("Arial", 10))
        priority_combo.set(reminder.get('priority', 'normal'))
        priority_combo.grid(row=row, column=1, pady=8, sticky=tk.W)
        
        row += 1
        
        # Voice note status
        current_voice = reminder.get('voice_note', '')
        voice_filename = os.path.basename(current_voice) if current_voice else "None"
        
        tk.Label(form, text="Voice Note:", bg='white', font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=8)
        voice_status_label = tk.Label(form, text=f"Current: {voice_filename}", bg='white', fg=COLORS['info'], font=("Arial", 9))
        voice_status_label.grid(row=row, column=1, pady=8, sticky=tk.W)
        
        row += 1
        
        new_voice_note = {'path': None}
        
        def record_new_voice():
            # Recording logic here (same as before)
            pass
        
        # Record button
        tk.Button(
            form,
            text="🎤 Record New Voice",
            command=record_new_voice,
            bg=COLORS['info'],
            fg='white',
            font=("Arial", 9, "bold"),
            padx=10,
            pady=5
        ).grid(row=row, column=1, pady=8, sticky=tk.W)
        
        row += 1
        
        # Save button
        def save():
            reminder['title'] = title_entry.get().strip()
            reminder['description'] = desc_entry.get().strip()
            reminder['date'] = date_entry.get_date().strftime("%Y-%m-%d")
            reminder['time'] = self.get_24hour_time(edit_hour_var.get(), edit_minute_var.get(), edit_ampm_var.get())
            reminder['priority'] = priority_combo.get()
            
            if new_voice_note['path']:
                reminder['voice_note'] = new_voice_note['path']
            
            self.save_data()
            self.refresh_reminders_list()
            messagebox.showinfo("Success", "Reminder updated!")
            dialog.destroy()
        
        # Action buttons
        btn_frame = tk.Frame(dialog, bg='white')
        btn_frame.pack(pady=20)
        
        tk.Button(
            btn_frame, 
            text="💾 Save Changes", 
            command=save, 
            bg=COLORS['success'], 
            fg='white',
            font=("Arial", 11, "bold"),
            padx=25, 
            pady=10
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Button(
            btn_frame, 
            text="❌ Cancel", 
            command=dialog.destroy, 
            bg=COLORS['danger'], 
            fg='white',
            font=("Arial", 11, "bold"),
            padx=25, 
            pady=10
        ).pack(side=tk.LEFT, padx=10)
    
    def get_24hour_time(self, hour, minute, ampm):
        hour = int(hour)
        minute = int(minute)
        if ampm == "AM" and hour == 12:
            hour = 0
        elif ampm == "PM" and hour != 12:
            hour += 12
        return f"{hour:02d}:{minute:02d}"
    
    def add_reminder_gui(self):
        """Add reminder"""
        title = self.reminder_title.get().strip()
        if not title:
            messagebox.showerror("Error", "Enter a title!")
            return
        
        reminder = {
            'id': int(time.time() * 1000),
            'title': title,
            'description': self.reminder_desc.get().strip(),
            'date': self.reminder_date.get_date().strftime("%Y-%m-%d"),
            'time': self.get_24hour_time(self.hour_var.get(), self.minute_var.get(), self.ampm_var.get()),
            'priority': self.reminder_priority.get(),
            'active': True
        }
        
        if self.pending_voice_note:
            reminder['voice_note'] = self.pending_voice_note
            self.pending_voice_note = None
        
        self.reminders.append(reminder)
        self.save_data()
        
        self.reminder_title.delete(0, tk.END)
        self.reminder_desc.delete(0, tk.END)
        
        self.refresh_reminders_list()
        messagebox.showinfo("Success", "Reminder added!")
    
    def refresh_reminders_list(self):
        """Refresh list"""
        if hasattr(self, 'reminders_listbox'):
            self.reminders_listbox.delete(0, tk.END)
            for r in self.reminders:
                if r['active']:
                    priority = "🔴" if r['priority'] == 'urgent' else "🟢"
                    voice = "🎤" if r.get('voice_note') else ""
                    try:
                        h24, m = r['time'].split(':')
                        h24 = int(h24)
                        ampm = "AM" if h24 < 12 else "PM"
                        h12 = h24 if h24 <= 12 else h24 - 12
                        if h12 == 0:
                            h12 = 12
                        time_display = f"{h12}:{m} {ampm}"
                    except:
                        time_display = r['time']
                    
                    text = f"{priority} {voice} {r['title']} | {r['date']} {time_display} | ID:{r['id']}"
                    self.reminders_listbox.insert(tk.END, text)
    
    def delete_reminder(self):
        """Delete reminder"""
        selection = self.reminders_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select a reminder!")
            return
        
        item_text = self.reminders_listbox.get(selection[0])
        try:
            reminder_id = int(item_text.split("ID:")[1].strip())
            self.reminders = [r for r in self.reminders if r['id'] != reminder_id]
            self.save_data()
            self.refresh_reminders_list()
            messagebox.showinfo("Success", "Deleted!")
        except:
            pass
    
    def check_reminders(self):
        """Check reminders"""
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        
        for reminder in self.reminders:
            if reminder['active'] and reminder['date'] == current_date and reminder['time'] == current_time:
                self.show_fullscreen_alert(
                    f"REMINDER: {reminder['title']}",
                    reminder['description'],
                    reminder['id'],
                    reminder.get('voice_note')
                )
                reminder['active'] = False
                self.save_data()
                if hasattr(self, 'root'):
                    try:
                        self.root.after(100, self.refresh_reminders_list)
                    except:
                        pass
    
    def load_data(self):
        """Load data"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    data = json.load(f)
                    self.reminders = data.get('reminders', [])
                    self.alarms = data.get('alarms', [])
            except:
                pass
    
    def save_data(self):
        """Save data"""
        with open(DATA_FILE, 'w') as f:
            json.dump({'reminders': self.reminders, 'alarms': self.alarms}, f, indent=2)
    
    def monitor_loop(self):
        """Monitor loop"""
        while self.running:
            try:
                self.check_reminders()
                self.check_snoozed()
            except:
                pass
            time.sleep(30)
    
    def start_monitor_thread(self):
        """Start monitor"""
        threading.Thread(target=self.monitor_loop, daemon=False).start()
    
    def on_closing(self):
        """Handle close"""
        if TRAY_AVAILABLE:
            self.hide_window()
        else:
            if messagebox.askokcancel("Quit", "Stop monitoring?"):
                self.quit_app()
    
    def run(self):
        """Run app"""
        try:
            self.root.mainloop()
        except:
            pass
        
        while self.running:
            time.sleep(1)

if __name__ == "__main__":
    print("="*60)
    print("🚀 REMINDER APP - AUTO-INSTALL EDITION")
    print("="*60)
    
    app = ReminderApp()
    app.run()
