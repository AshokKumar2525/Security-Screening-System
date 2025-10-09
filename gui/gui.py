import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import cv2
import time
import os

LOG_DIR = "csv_logs"

# --- Simple Tooltip helper for ttk/tk widgets ---
class ToolTip:
    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        widget.bind("<Enter>", self._enter)
        widget.bind("<Leave>", self._leave)
        widget.bind("<ButtonPress>", self._leave)

    def _enter(self, event=None):
        self._schedule()

    def _leave(self, event=None):
        self._unschedule()
        self._hidetip()

    def _schedule(self):
        self._unschedule()
        self.id = self.widget.after(self.delay, self._showtip)

    def _unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def _showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        # Some widgets (e.g., ttk.Button) don't support bbox("insert").
        if self.widget.winfo_ismapped():
            try:
                x, y, cx, cy = self.widget.bbox("insert")
            except Exception:
                x, y, cx, cy = (0, 0, 0, 0)
        else:
            x, y, cx, cy = (0, 0, 0, 0)
        x = x + self.widget.winfo_rootx() + 20
        y = y + self.widget.winfo_rooty() + 35
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#333333", foreground="white",
                         relief=tk.SOLID, borderwidth=1,
                         font=("Segoe UI", 9))
        label.pack(ipadx=6, ipady=4)

    def _hidetip(self):
        tw = self.tipwindow
        if tw:
            tw.destroy()
            self.tipwindow = None

class guiwindow:
    def __init__(self, get_frame_callback, status_callback=None, start_camera_callback=None):
        self.root = tk.Tk()
        self.root.title("Security Screening System")
        self.root.geometry("1000x800")
        self.root.resizable(False, False)
        self.root.configure(bg='#1e1e1e')

        # --- Style ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background='#1e1e1e')
        self.style.configure("TLabel", background='#1e1e1e', foreground='white', font=("Segoe UI", 12))
        self.style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"))
        self.style.configure("Status.TLabel", font=("Segoe UI", 14, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 12, "bold"), foreground="white")
        self.style.map("TButton",
                       background=[('active', '#005f5f'), ('!disabled', '#008080')],
                       foreground=[('disabled', '#a9a9a9')])

        # Load threshold value from config or use default
        initial_threshold = self.load_threshold_from_config()
        
        # Threshold configuration variables
        self.threshold_var = tk.DoubleVar(value=initial_threshold)
        self.threshold_frame_visible = False

        # --- Header ---
        self.header_frame = ttk.Frame(self.root)
        self.header_frame.pack(pady=20)
        self.header_label = ttk.Label(self.header_frame, text="Security Screening System", style="Title.TLabel")
        self.header_label.pack()

        # --- Video Feed ---
        self.video_frame = ttk.Frame(self.root, padding=6)
        self.video_frame.pack()
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.pack()
        self.video_label.configure(background='black')

        # --- Status Panel ---
        self.status_panel = ttk.Frame(self.root, padding=10)
        self.status_panel.pack(pady=20)
        self.status_indicator = tk.Canvas(self.status_panel, width=20, height=20, bg='#1e1e1e', highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 10))
        self.status_label = ttk.Label(self.status_panel, text="Initializing system...", style="Status.TLabel")
        self.status_label.pack(side=tk.LEFT)
        self.update_status_indicator('gray')

        # --- Control Panel ---
        self.control_panel = ttk.Frame(self.root, padding=10)
        self.control_panel.pack(pady=10)

        self.start_button = ttk.Button(self.control_panel, text="▶️ Start Camera", command=self.start_camera, width=20)
        self.start_button.grid(row=0, column=0, padx=10)

        self.pause_button = ttk.Button(self.control_panel, text="⏸️ Pause", command=self.toggle_pause, width=20, state="disabled")
        self.pause_button.grid(row=0, column=1, padx=10)

        self.export_log_button = ttk.Button(self.control_panel, text="📊 Export Log", command=self.export_log, width=20, state="disabled")
        self.export_log_button.grid(row=0, column=2, padx=10)

        # About button (non-intrusive)
        self.about_button = ttk.Button(self.control_panel, text="ℹ️ About", command=self.show_about, width=14)
        self.about_button.grid(row=0, column=3, padx=10)

        # Threshold configuration button
        self.threshold_button = ttk.Button(
            self.control_panel, 
            text="⚙️ Threshold", 
            command=self.toggle_threshold_settings,
            width=14
        )
        self.threshold_button.grid(row=0, column=4, padx=10)

        # Tooltips
        ToolTip(self.start_button, "Start camera (Ctrl+S). Initializes webcam and status announcements.")
        ToolTip(self.pause_button, "Pause/Resume detection (Space). Keeps the last frame visible.")
        ToolTip(self.export_log_button, "Export csv_logs/security_log.csv to a chosen location (Ctrl+E).")
        ToolTip(self.about_button, "About this application.")
        ToolTip(self.threshold_button, "Adjust recognition strictness (0.1-0.39)")

        # Keyboard shortcuts
        self.root.bind("<Control-s>", lambda e: self.start_camera())
        self.root.bind_all("<space>", lambda e: self.toggle_pause())
        self.root.bind("<Control-e>", lambda e: self.export_log())

        # Setup threshold controls
        self.setup_threshold_controls()

        self.get_frame = get_frame_callback
        self.status_callback = status_callback
        self.start_camera_callback = start_camera_callback
        
        self._get_is_paused = None
        self._set_is_paused = None
        self._get_pause_start_time = None
        self._set_pause_start_time = None
        self._get_paused_names_time = None
        self._set_paused_names_time = None
        self._get_detection_time = None

        self.camera_started = False
        
        # Update slider when variable changes
        def update_threshold_display(*args):
            if hasattr(self, 'slider_canvas'):
                self.draw_slider()
        
        self.threshold_var.trace('w', update_threshold_display)
        
        self.update_frame()

    def load_threshold_from_config(self):
        """Load threshold value from config file, return default if not exists"""
        try:
            config_path = "config/system_config.json"
            if os.path.exists(config_path):
                import json
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    threshold = config_data.get('recognition_threshold', 0.4)
                    last_updated = config_data.get('last_updated', 'Never')
                    print(f"[Config] Loaded threshold from config: {threshold} (Last updated: {last_updated})")
                    return threshold
        except Exception as e:
            print(f"[Config] Error loading threshold config: {e}")
        
        # Return default if config doesn't exist or error occurs
        return 0.4

    def save_threshold_to_config(self, threshold_value):
        """Save threshold value to config file for next startup"""
        try:
            import json
            config_dir = "config"
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            config_path = os.path.join(config_dir, "system_config.json")
            current_time = time.ctime()
            config_data = {
                        'recognition_threshold': threshold_value,
                        'last_updated': current_time
                }            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            print(f"[Config] Threshold saved to config: {threshold_value} at {current_time}")
        except Exception as e:
            print(f"[Config] Error saving threshold config: {e}")

    def setup_threshold_controls(self):
        """Add threshold configuration controls to GUI"""
        # Threshold settings frame (initially hidden)
        self.threshold_settings_frame = ttk.LabelFrame(self.root, text="⚙️ Recognition Strictness Settings",
                                                       padding=15,style='Custom.TLabelframe')
        
        self.style.configure('Custom.TLabelframe', background='white', foreground='black',bordercolor='#555555')
        self.style.configure('Custom.TLabelframe.Label', background='white', foreground='black')
        self.style.configure('Custom.TFrame', background='white')
        
        container = ttk.Frame(self.threshold_settings_frame, style='Custom.TFrame')
        container.pack(fill='x', padx=5, pady=5)
        
        info_text = "• Lower values = More strict (fewer matches, higher confidence required)\n• Range: 0.10 to 0.39 | Default: 0.40\n• Configure before starting camera"
        info_label = ttk.Label(container, text=info_text, font=("Segoe UI", 9), foreground='#333333',
                                background='white', justify=tk.LEFT)
        info_label.pack(anchor='w', pady=(0, 15))
        
        # Slider frame
        slider_frame = ttk.Frame(container, style='Custom.TFrame')
        slider_frame.pack(fill='x', pady=8)
        
        ttk.Label(slider_frame, text="Threshold:", 
                 foreground='black', background='white').pack(side=tk.LEFT, padx=(0, 15))
        
        self.create_custom_slider(slider_frame)
        
        # Button frame
        button_frame = ttk.Frame(container, style='Custom.TFrame')
        button_frame.pack(fill='x', pady=(15, 5))
        
        self.apply_threshold_btn = tk.Button(
            button_frame,
            text="✅ Apply Threshold",
            command=self.apply_threshold,
            bg='#4CAF50',
            fg='white',
            font=("Segoe UI", 10, "bold"),
            relief='raised',
            bd=2,
            padx=15,
            pady=5,
            cursor='hand2'
        )
        self.apply_threshold_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Reset button
        self.reset_threshold_btn = tk.Button(
            button_frame,
            text="🔄 Reset to Default", 
            command=self.reset_threshold,
            bg='#FF9800',
            fg='white',
            font=("Segoe UI", 10, "bold"),
            relief='raised',
            bd=2,
            padx=15,
            pady=5,
            cursor='hand2'
        )
        self.reset_threshold_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Close button
        self.close_threshold_btn = tk.Button(
            button_frame,
            text="❌ Close",
            command=self.toggle_threshold_settings,
            bg='#f44336',
            fg='white', 
            font=("Segoe UI", 10, "bold"),
            relief='raised',
            bd=2,
            padx=15,
            pady=5,
            cursor='hand2'
        )
        self.close_threshold_btn.pack(side=tk.LEFT)

    def create_custom_slider(self, parent):
        """Create a custom interactive slider with green progress bar"""
        # Main slider container
        slider_container = ttk.Frame(parent, style='Custom.TFrame')
        slider_container.pack(side=tk.LEFT, fill='x', expand=True)
        
        # Create canvas for custom slider with more vertical space
        self.slider_canvas = tk.Canvas(
            slider_container,
            height=60, 
            bg='white',
            highlightthickness=0
        )
        self.slider_canvas.pack(fill='x', pady=5)
        self.slider_width = 250
        self.slider_height = 8
        self.slider_x = 10
        self.slider_y = 40
        self.knob_radius = 10
        
        # Draw initial slider
        self.draw_slider()
        
        # Bind mouse events for interactivity
        self.slider_canvas.bind("<Button-1>", self.on_slider_click)
        self.slider_canvas.bind("<B1-Motion>", self.on_slider_drag)
        self.slider_canvas.bind("<Enter>", lambda e: self.slider_canvas.config(cursor='hand2'))
        self.slider_canvas.bind("<Leave>", lambda e: self.slider_canvas.config(cursor=''))

    def draw_slider(self):
        """Draw the slider with green progress bar"""
        self.slider_canvas.delete("all")
        
        # Calculate current position
        current_value = self.threshold_var.get()
        normalized_pos = (current_value - 0.1) / (0.39 - 0.1)  # Normalize to 0-1
        knob_x = self.slider_x + (normalized_pos * self.slider_width)
        
        # Draw track background
        self.slider_canvas.create_rectangle(
            self.slider_x, 
            self.slider_y - self.slider_height//2,
            self.slider_x + self.slider_width, 
            self.slider_y + self.slider_height//2,
            fill='#cccccc',
            outline='#999999',
            width=1
        )
        
        # Draw progress bar (green filled portion)
        self.slider_canvas.create_rectangle(
            self.slider_x, 
            self.slider_y - self.slider_height//2,
            knob_x, 
            self.slider_y + self.slider_height//2,
            fill='#4CAF50',
            outline='',
            width=0
        )
        
        # Draw value indicator ABOVE the track (in the empty space we created)
        text_y = 15 
        
        # Text with nice styling - changed to black
        self.slider_canvas.create_text(
            knob_x,
            text_y,
            text=f"{current_value:.2f}",
            fill='black',
            font=("Segoe UI", 10, "bold")
        )
        
        # Draw a line connecting text to knob for better visual connection
        self.slider_canvas.create_line(
            knob_x,
            text_y + 8, 
            knob_x,
            self.slider_y - self.knob_radius - 2, 
            fill='#666666',
            width=1,
            dash=(2, 2)
        )
        
        # Draw knob (after text so it appears on top)
        self.slider_canvas.create_oval(
            knob_x - self.knob_radius,
            self.slider_y - self.knob_radius,
            knob_x + self.knob_radius, 
            self.slider_y + self.knob_radius,
            fill='#2196F3',
            outline='#1976D2',
            width=2
        )

    def on_slider_click(self, event):
        """Handle slider click"""
        self.on_slider_drag(event)

    def on_slider_drag(self, event):
        """Handle slider dragging"""
        # Calculate normalized position
        rel_x = max(0, min(event.x - self.slider_x, self.slider_width))
        normalized_pos = rel_x / self.slider_width
        
        # Convert to actual value
        new_value = 0.1 + (normalized_pos * (0.39 - 0.1))
        new_value = round(new_value, 2) 
        
        # Update variable and redraw
        self.threshold_var.set(new_value)
        self.draw_slider()

    def toggle_threshold_settings(self):
        """Show/hide threshold settings frame"""
        if not self.threshold_frame_visible:
            self.threshold_settings_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            self.threshold_frame_visible = True
            self.threshold_button.config(text="⚙️ Hide Threshold")
        else:
            self.threshold_settings_frame.place_forget()
            self.threshold_frame_visible = False
            self.threshold_button.config(text="⚙️ Threshold")

    def apply_threshold(self):
        """Apply the selected threshold value"""
        threshold_value = self.threshold_var.get()
        
        # Update the security system's threshold
        if hasattr(self, 'get_frame'):
            security_system = self.get_frame.__self__
            security_system.user_conf_threshold = threshold_value
            security_system.save_threshold_settings()
            
        # Also save to config file directly for GUI to load next time
        self.save_threshold_to_config(threshold_value)
            
        self.update_status(f"Recognition threshold set to: {threshold_value:.2f}", "light blue")
        print(f"[Config] Recognition threshold updated to: {threshold_value:.2f}")
        
        self.draw_slider()
        self.toggle_threshold_settings()

    def reset_threshold(self):
        """Reset threshold to default value and auto-close"""
        self.threshold_var.set(0.4)
        self.draw_slider()  
        self.apply_threshold()  

    def update_status_indicator(self, color):
        self.status_indicator.delete("all")
        self.status_indicator.create_oval(2, 2, 18, 18, fill=color, outline=color)

    def export_log(self):
        log_file = os.path.join(LOG_DIR, "security_log.csv")
        if os.path.exists(log_file):
            export_file = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv")],
                initialfile="exported_log.csv",
                title="Choose Export Location"
            )
            if export_file:
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    with open(export_file, "w", encoding="utf-8") as ef:
                        ef.write(content)
                    self.update_status(f"Log exported successfully to {export_file}!", color='green')
                except Exception as e:
                    self.update_status(f"Export failed: {e}", color='red')
            else:
                self.update_status("Export cancelled by user.", color='orange')
        else:
            self.update_status("No log file found!", color='red')

    def set_pause_vars(
        self,
        get_is_paused, set_is_paused,
        get_pause_start_time, set_pause_start_time,
        get_paused_names_time, set_paused_names_time,
        get_detection_time
    ):
        self._get_is_paused = get_is_paused
        self._set_is_paused = set_is_paused
        self._get_pause_start_time = get_pause_start_time
        self._set_pause_start_time = set_pause_start_time
        self._get_paused_names_time = get_paused_names_time
        self._set_paused_names_time = set_paused_names_time
        self._get_detection_time = get_detection_time

    def toggle_pause(self):
        if not self.camera_started:
            self.update_status("Camera not started", "gray")
            return

        if not self._get_is_paused():
            self._set_is_paused(True)
            self._set_pause_start_time(time.time())
            detection_time = self._get_detection_time()
            paused_names_time = {name: time.time() - t for name, t in detection_time.items()}
            self._set_paused_names_time(paused_names_time)
            self.pause_button.config(text="▶️ Resume")
            self.style.map("TButton", background=[('active', '#005f5f'), ('!disabled', '#00af5f')])

        else:
            self._set_is_paused(False)
            pause_duration = time.time() - self._get_pause_start_time()
            detection_time = self._get_detection_time()
            paused_names_time = self._get_paused_names_time()
            for name in detection_time:
                detection_time[name] = time.time() - paused_names_time.get(name, 0)
            self._set_pause_start_time(None)
            self._set_paused_names_time({})
            self.pause_button.config(text="⏸️ Pause")
            self.style.map("TButton", background=[('active', '#005f5f'), ('!disabled', '#008080')])


    def start_camera(self):
        if not self.camera_started:
            if self.start_camera_callback:
                self.start_camera_callback()
            self.camera_started = True
            self.start_button.config(state="disabled")
            self.pause_button.config(state="normal")
            self.export_log_button.config(state="normal")
            
            # Disable threshold controls
            self.threshold_button.config(state="disabled")
            if self.threshold_frame_visible:
                self.toggle_threshold_settings() 
                
            self.update_status("Camera starting...", color="green")
        else:
            self.update_status("Camera already started", color="green")

    def update_frame(self):
        frame = self.get_frame()
        if frame is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)

        if self.status_callback:
            status_text, status_color = self.status_callback()
            self.update_status(status_text, status_color)

        self.root.after(10, self.update_frame)

    def update_status(self, message, color='white'):
        self.status_label.config(text=message, foreground=color)
        self.update_status_indicator(color)

    def show_about(self):
        message = (
            "Security Screening System\n\n"
            "This GUI provides Start/Pause controls, status feedback, and log export.\n"
            "Shortcuts: Ctrl+S Start, Space Pause/Resume, Ctrl+E Export Log.\n"
            "Threshold Settings: Adjust recognition strictness (0.1-0.39) for different environments.\n"
            "Lower values = More strict (fewer matches, higher confidence required)."
        )
        messagebox.showinfo("About", message)

    def run(self):
        self.root.mainloop()