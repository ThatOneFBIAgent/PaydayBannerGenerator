import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
import cv2
import numpy as np
import threading
import time
import math
import os
import sys
import re
from datetime import datetime

# Directory Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")


def check_required_folders():
    """Check for required folders at startup. Returns (success, error_message)."""

    # Check for exports folder
    if not os.path.isdir(EXPORTS_DIR):
        try:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
        except Exception:
            pass
    
    return True, None
# TODO: fix this so it doesnt make it in the user directory

def sanitize_filename(text, max_length=50):
    """Sanitize text for use in filenames."""
    sanitized = re.sub(r'[<>:"/\\|?*]', '', text)
    sanitized = re.sub(r'\s+', '_', sanitized.strip())
    sanitized = sanitized[:max_length]  # Truncate if too long
    return sanitized if sanitized else "export"


def generate_export_filename(banner_text, fmt):
    """Generate an auto-filename for exports based on banner text and timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = sanitize_filename(banner_text)
    return f"{base_name}_{timestamp}.{fmt}"


class BannerRenderer: 
    # Fallback font chain - tried in order until one works
    FALLBACK_FONTS = [
        "impact.ttf",
        "Impact.ttf",
        "arialbd.ttf", 
        "Arial Bold.ttf",
        "arial.ttf",
        "Arial.ttf",
        "Arial"
    ]
    
    def __init__(self, config): 
        self.config = config 
        self.font_path = None
        
        # Check if a specific font is set in config
        config_font = config.get('font', '')
        if config_font:
            # Try to use the configured font (could be family name or file path)
            for variant in [config_font, f"{config_font}.ttf", config_font.lower().replace(' ', '') + ".ttf"]:
                try:
                    ImageFont.truetype(variant, 40)
                    self.font_path = variant
                    break
                except:
                    continue
        
        # If selected font failed or none set, try fallback chain
        if not self.font_path:
            # First check for local .ttf files in script directory
            local_fonts = []
            try:
                for bf in os.listdir(os.getcwd()):
                    if bf.endswith(".ttf"):
                        local_fonts.append(bf)
            except:
                pass
            
            # Try local fonts first, then fallbacks
            for f in local_fonts + self.FALLBACK_FONTS: 
                try: 
                    ImageFont.truetype(f, 40) 
                    self.font_path = f 
                    break 
                except: 
                    continue
        
        # Ultimate fallback
        if not self.font_path:
            self.font_path = "arial.ttf"
        

    def get_skulls(self, level_input):
        levels = {
            "Easy (0 skulls)": 0,
            "Normal (1 skull)": 1,
            "Hard (2 skulls)": 2,
            "Overkill (3 skulls)": 3,
            "Mayhem (4 skulls)": 4,
            "Death Wish (5 skulls)": 5,
            "Death Sentence (6 skulls)": 6,
            "Juggernaut (7 skulls)": 7,
            "Apocalypse (8 skulls)": 8,
            "Cataclysmic (9 skulls)": 9,
            "Armageddon (10 skulls)": 10
        }
        
        count = 0
        if isinstance(level_input, int):
            count = level_input
        else:
            count = levels.get(level_input, 1)
            
        return " " + " ".join(["\u2126"] * count) + " "

    def draw_frame(self, time_sec, width, height_mode, height_val, padding):
        BANNER_HEIGHT = 80
        INDICATOR_SIZE = 60
        FONT_SIZE = 40
        
        if height_mode == "fixed":
            canvas_height = 1080
            canvas_width = width
            center_y = canvas_height // 2
        else:
            canvas_height = BANNER_HEIGHT + (padding * 2)
            canvas_width = width
            center_y = canvas_height // 2

        # Main Canvas (Transparent)
        img = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0)) 
        draw = ImageDraw.Draw(img)
        
        # Parse Colors
        main_color_hex = self.config.get('color', '#FFEF00')
        bg_color_1_hex = self.config.get('bg_color_1', '#FFEF00') 
        bg_color_2_hex = self.config.get('bg_color_2', '#BDB200')
        
        main_color_rgb = tuple(int(main_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        bg_c1_rgb = tuple(int(bg_color_1_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        bg_c2_rgb = tuple(int(bg_color_2_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        # --- Animation Variables ---
        has_intro_anim = self.config.get('start_flicker', False)
        flicker_duration = self.config.get('start_flicker_duration', 2.0) if has_intro_anim else 0.0
        start_time = flicker_duration
        expand_dur = 0.45 if has_intro_anim else 0.0  # Skip expansion when flicker is disabled
        
        # Indicator Flicker
        indicator_opacity = 255
        if has_intro_anim and time_sec < flicker_duration:
            phase = (time_sec % 0.5) / 0.5
            if phase > 0.5:
                indicator_opacity = 0
            else:
                indicator_opacity = 255

        # Banner Width Calculation
        target_banner_width = canvas_width - 100 
        current_banner_width = 0
        
        if not has_intro_anim:
            # No intro animation - show full banner immediately
            current_banner_width = target_banner_width
        elif time_sec < start_time:
            current_banner_width = 0
        elif time_sec < start_time + expand_dur:
            progress = (time_sec - start_time) / expand_dur
            current_banner_width = int(target_banner_width * progress)
        else:
            current_banner_width = target_banner_width

        # Background Flicker Interpolation
        current_bg_rgb = bg_c1_rgb
        if time_sec > start_time + expand_dur:
            loop_time = time_sec - (start_time + expand_dur)
            speed_mult = self.config.get('bg_flicker_speed', 1.0)
            mix_factor = 0.0
            
            if speed_mult > 0:
                cycle = (loop_time * speed_mult) % 1.0
                # Triangle wave 0->1->0
                if cycle < 0.5:
                    mix_factor = cycle / 0.5 
                else:
                    mix_factor = 1.0 - ((cycle - 0.5) / 0.5)
            
            r = int(bg_c1_rgb[0] + (bg_c2_rgb[0] - bg_c1_rgb[0]) * mix_factor)
            g = int(bg_c1_rgb[1] + (bg_c2_rgb[1] - bg_c1_rgb[1]) * mix_factor)
            b = int(bg_c1_rgb[2] + (bg_c2_rgb[2] - bg_c1_rgb[2]) * mix_factor)
            current_bg_rgb = (r, g, b)
        
        # Layout Coordinates
        offset_x = (canvas_width - target_banner_width - INDICATOR_SIZE) // 2
        banner_x = offset_x
        banner_y = center_y - (BANNER_HEIGHT // 2)
        
        indicator_x = banner_x + current_banner_width + 10 
        indicator_y = center_y - (INDICATOR_SIZE // 2)
        
        # Draw Banner
        if current_banner_width > 0:
            banner_bg_color = (*current_bg_rgb, 180)
            banner_surf = Image.new('RGBA', (current_banner_width, BANNER_HEIGHT), banner_bg_color)
            b_draw = ImageDraw.Draw(banner_surf)
            
            # Draw Marquee Text on Banner Surface
            base_msg = "POLICE ASSAULT IN PROGRESS" 
            if self.config.get('custom_text'):
                base_msg = self.config.get('custom_text').upper()
            
            threat = self.config.get('threat_level', 'Normal (1 skull)')
            suffix = " /// " + self.get_skulls(threat) + " /// "
            full_text_unit = base_msg + suffix
            
            try:
                font = ImageFont.truetype(self.font_path, FONT_SIZE)
            except:
                font = ImageFont.load_default()
            
            # Calculate Scrolling
            scroll_speed = 200
            curr_scroll_time = 0
            if time_sec > start_time + expand_dur:
                curr_scroll_time = time_sec - (start_time + expand_dur)
            
            scroll_offset = int(curr_scroll_time * scroll_speed)
            
            text_bbox = b_draw.textbbox((0,0), full_text_unit, font=font)
            unit_width = text_bbox[2] - text_bbox[0]
            if unit_width < 1: unit_width = 100
            
            start_draw_x = -(scroll_offset % unit_width)
            text_y = (BANNER_HEIGHT - FONT_SIZE) // 2 - 5
            text_fill = (*main_color_rgb, 255)
            
            draw_x = start_draw_x
            while draw_x < current_banner_width:
                b_draw.text((draw_x, text_y), full_text_unit, font=font, fill=text_fill)
                draw_x += unit_width

            # Draw Corner Accents on Banner Surface
            corner_len = 20
            corner_thick = 3
            c_fill = (*main_color_rgb, 255)
            
            w = current_banner_width
            h = BANNER_HEIGHT
            
            # Top-Left
            b_draw.rectangle([0, 0, corner_len, corner_thick], fill=c_fill)
            b_draw.rectangle([0, 0, corner_thick, corner_len], fill=c_fill)
            
            # Top-Right
            b_draw.rectangle([w - corner_len, 0, w, corner_thick], fill=c_fill)
            b_draw.rectangle([w - corner_thick, 0, w, corner_len], fill=c_fill)
            
            # Bot-Left
            b_draw.rectangle([0, h - corner_thick, corner_len, h], fill=c_fill)
            b_draw.rectangle([0, h - corner_len, corner_thick, h], fill=c_fill)
            
            # Bot-Right
            b_draw.rectangle([w - corner_len, h - corner_thick, w, h], fill=c_fill)
            b_draw.rectangle([w - corner_thick, h - corner_len, w, h], fill=c_fill)

            # Paste Banner onto Main Image
            img.paste(banner_surf, (banner_x, banner_y))

        # Draw Indicator
        if indicator_opacity > 0:
            ind_color = (*main_color_rgb, indicator_opacity)
            draw.rectangle([indicator_x, indicator_y, indicator_x + INDICATOR_SIZE, indicator_y + INDICATOR_SIZE], fill=ind_color)
            
            ix, iy = indicator_x, indicator_y
            pad = 12
            p1 = (ix + INDICATOR_SIZE//2, iy + pad) 
            p2 = (ix + INDICATOR_SIZE - pad, iy + INDICATOR_SIZE - pad) 
            p3 = (ix + pad, iy + INDICATOR_SIZE - pad) 
            
            points = [p1, p2, p3, p1]
            draw.line(points, fill=(0,0,0, indicator_opacity), width=7, joint="curve")

        return img

    def estimate_loop_duration(self):
        """
        Calculate the optimal GIF loop duration that ensures both the text scroll
        and background flicker animations complete full cycles for seamless looping.
        """
        base_msg = "POLICE ASSAULT IN PROGRESS" 
        if self.config.get('custom_text'):
            base_msg = self.config.get('custom_text').upper()
        
        threat = self.config.get('threat_level', 'Normal (1 skull)')
        suffix = " /// " + self.get_skulls(threat) + " /// "
        full_text_unit = base_msg + suffix
        
        try:
            font = ImageFont.truetype(self.font_path, 40)
        except:
            font = ImageFont.load_default()
            
        dummy = ImageDraw.Draw(Image.new('L', (1,1)))
        bbox = dummy.textbbox((0,0), full_text_unit, font=font)
        unit_width = bbox[2] - bbox[0]
        
        scroll_speed = 200 
        text_cycle = unit_width / scroll_speed  # Duration for one full text scroll
        
        # Calculate background flicker cycle duration
        bg_speed = self.config.get('bg_flicker_speed', 1.0)
        if bg_speed > 0:
            # One flicker cycle is 1.0 / bg_speed seconds (triangle wave goes 0->1->0)
            flicker_cycle = 1.0 / bg_speed
        else:
            flicker_cycle = 0
        
        # Find the optimal loop duration
        if flicker_cycle <= 0:
            return text_cycle
        else:
            # Find LCM of both cycle durations for perfect loop
            return self._find_lcm_duration(text_cycle, flicker_cycle)
    
    def _find_lcm_duration(self, cycle_a, cycle_b, max_loops=10, tolerance=0.05):
        """
        Find the smallest duration where both cycles align within tolerance.
        This ensures smooth looping for both animations.
        
        Args:
            cycle_a: First cycle duration (e.g., text scroll)
            cycle_b: Second cycle duration (e.g., background flicker)
            max_loops: Maximum number of cycle_a repetitions to check
            tolerance: Acceptable alignment error as a fraction of cycle_b
        
        Returns:
            Duration in seconds for optimal loop
        """
        if cycle_a <= 0:
            return cycle_b
        if cycle_b <= 0:
            return cycle_a
            
        # Check multiples of cycle_a to find one that aligns with cycle_b
        for n in range(1, max_loops + 1):
            duration = cycle_a * n
            remainder = duration % cycle_b
            if remainder < (cycle_b * tolerance) or remainder > (cycle_b * (1 - tolerance)):
                return duration
        
        # and if we can't find a match, just use the text cycle
        return cycle_a

# Dark and light theme defs
THEMES = {
    'dark': {
        'bg': '#1a1a1a',
        'bg_secondary': '#252525',
        'bg_tertiary': '#2d2d2d',
        'fg': '#e0e0e0',
        'fg_dim': '#888888',
        'accent': '#FFEF00',
        'accent_dark': '#C4B500',
        'accent_hover': '#FFE500',
        'border': '#3d3d3d',
        'entry_bg': '#1f1f1f',
        'button_bg': '#333333',
        'button_hover': '#404040',
        'preview_bg': '#0a0a0a',
        'section_header': '#FFEF00',
    },
    'light': {
        'bg': '#f0f0f0',
        'bg_secondary': '#ffffff',
        'bg_tertiary': '#e8e8e8',
        'fg': '#1a1a1a',
        'fg_dim': '#666666',
        'accent': '#C4A000',
        'accent_dark': '#8B7500',
        'accent_hover': '#DAAE00',
        'border': '#cccccc',
        'entry_bg': '#ffffff',
        'button_bg': '#e0e0e0',
        'button_hover': '#d0d0d0',
        'preview_bg': '#2a2a2a',
        'section_header': '#8B7500',
    }
}


class PaydayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PAYDAY 2 — Assault Banner Generator")
        self.root.geometry("1280x800")
        self.root.minsize(1000, 700)
        
        # Theme state
        self.current_theme = 'dark'
        self.theme = THEMES[self.current_theme]
        
        self.config = {
            'custom_text': 'POLICE ASSAULT IN PROGRESS',
            'threat_level': 'Normal (1 skull)',
            'color': '#FFEF00',
            'bg_color_1': '#C4B500',
            'bg_color_2': '#645C00',
            'auto_bg_color': True,  # Auto-generate background colors from main color
            'start_flicker': True,
            'start_flicker_duration': 2.0,  # Duration of the blinking intro animation
            'bg_flicker_speed': 1.0,
            'canvas_width': 720,
            'canvas_height_mode': 'fit',
            'fit_padding': 10
        }
        
        self.renderer = BannerRenderer(self.config)
        self.preview_running = True
        self.start_time = time.time()
        
        self.setup_styles()
        self.build_ui()
        self.animate_preview()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def on_close(self):
        self.preview_running = False
        self.root.destroy()

    def setup_styles(self):
        """Configure ttk styles for the current theme."""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        t = self.theme
        
        # Configure root
        self.root.configure(bg=t['bg'])
        
        # Frame styles
        self.style.configure('TFrame', background=t['bg'])
        self.style.configure('Secondary.TFrame', background=t['bg_secondary'])
        self.style.configure('Card.TFrame', background=t['bg_secondary'])
        
        # Label styles
        self.style.configure('TLabel', 
            background=t['bg_secondary'], 
            foreground=t['fg'],
            font=('Segoe UI', 10))
        self.style.configure('Header.TLabel',
            background=t['bg'],
            foreground=t['accent'],
            font=('Segoe UI', 14, 'bold'))
        self.style.configure('Section.TLabel',
            background=t['bg_secondary'],
            foreground=t['section_header'],
            font=('Segoe UI', 11, 'bold'))
        self.style.configure('Dim.TLabel',
            background=t['bg_secondary'],
            foreground=t['fg_dim'],
            font=('Segoe UI', 9))
            
        # Entry styles
        self.style.configure('TEntry',
            fieldbackground=t['entry_bg'],
            foreground=t['fg'],
            insertcolor=t['fg'],
            borderwidth=1)
        self.style.map('TEntry',
            fieldbackground=[('focus', t['entry_bg'])],
            bordercolor=[('focus', t['accent'])])
            
        # Combobox styles
        self.style.configure('TCombobox',
            fieldbackground=t['entry_bg'],
            background=t['button_bg'],
            foreground=t['fg'],
            arrowcolor=t['accent'])
        self.style.map('TCombobox',
            fieldbackground=[('readonly', t['entry_bg'])],
            selectbackground=[('readonly', t['accent'])],
            selectforeground=[('readonly', t['bg'])])
            
        # Button styles
        self.style.configure('TButton',
            background=t['button_bg'],
            foreground=t['fg'],
            font=('Segoe UI', 10),
            padding=(12, 6))
        self.style.map('TButton',
            background=[('active', t['button_hover']), ('pressed', t['accent_dark'])],
            foreground=[('active', t['fg'])])
            
        # Accent button
        self.style.configure('Accent.TButton',
            background=t['accent'],
            foreground='#000000',
            font=('Segoe UI', 11, 'bold'),
            padding=(20, 10))
        self.style.map('Accent.TButton',
            background=[('active', t['accent_hover']), ('pressed', t['accent_dark'])])
            
        # Checkbutton
        self.style.configure('TCheckbutton',
            background=t['bg_secondary'],
            foreground=t['fg'],
            font=('Segoe UI', 10))
        self.style.map('TCheckbutton',
            background=[('active', t['bg_secondary'])])
            
        # Radiobutton
        self.style.configure('TRadiobutton',
            background=t['bg_secondary'],
            foreground=t['fg'],
            font=('Segoe UI', 10))
        self.style.map('TRadiobutton',
            background=[('active', t['bg_secondary'])])
            
        # Scale
        self.style.configure('TScale',
            background=t['bg_secondary'],
            troughcolor=t['bg_tertiary'])
            
        # Spinbox
        self.style.configure('TSpinbox',
            fieldbackground=t['entry_bg'],
            background=t['button_bg'],
            foreground=t['fg'],
            arrowcolor=t['accent'])
            
        # Progressbar
        self.style.configure('TProgressbar',
            background=t['accent'],
            troughcolor=t['bg_tertiary'])
        
    def build_ui(self):
        """Build the main UI layout."""
        t = self.theme
        
        # Header bar
        header = ttk.Frame(self.root, style='TFrame')
        header.pack(fill='x', padx=15, pady=(15, 10))
        
        # Title with Payday styling
        title_frame = ttk.Frame(header, style='TFrame')
        title_frame.pack(side='left')
        
        title_lbl = tk.Label(header, 
            text="◢ PAYDAY 2 — ASSAULT BANNER GENERATOR ◣",
            bg=t['bg'], 
            fg=t['accent'],
            font=('Segoe UI', 16, 'bold'))
        title_lbl.pack(side='left')
        
        # Theme toggle
        theme_frame = ttk.Frame(header, style='TFrame')
        theme_frame.pack(side='right')
        
        self.theme_var = tk.StringVar(value=self.current_theme)
        
        dark_rb = ttk.Radiobutton(theme_frame, text="◐ Dark", 
            variable=self.theme_var, value='dark',
            command=self.toggle_theme)
        dark_rb.pack(side='left', padx=5)
        
        light_rb = ttk.Radiobutton(theme_frame, text="◑ Light",
            variable=self.theme_var, value='light', 
            command=self.toggle_theme)
        light_rb.pack(side='left', padx=5)
        
        # Main content area (Side by Side)
        main_container = ttk.Frame(self.root, style='TFrame')
        main_container.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        
        # Left panel - Controls (scrollable)
        left_panel = ttk.Frame(main_container, style='TFrame')
        left_panel.pack(side='left', fill='y', padx=(0, 10))
        
        # Create scrollable canvas for controls
        controls_canvas = tk.Canvas(left_panel, bg=t['bg'], 
            highlightthickness=0, width=380)
        controls_scrollbar = ttk.Scrollbar(left_panel, orient='vertical',
            command=controls_canvas.yview)
        self.controls_frame = ttk.Frame(controls_canvas, style='TFrame')
        
        self.controls_frame.bind('<Configure>', 
            lambda e: controls_canvas.configure(scrollregion=controls_canvas.bbox('all')))
        controls_canvas.create_window((0, 0), window=self.controls_frame, anchor='nw')
        controls_canvas.configure(yscrollcommand=controls_scrollbar.set)
        
        controls_canvas.pack(side='left', fill='both', expand=True)
        controls_scrollbar.pack(side='right', fill='y')
        
        # Enable mousewheel scrolling
        def on_mousewheel(event):
            controls_canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        controls_canvas.bind_all('<MouseWheel>', on_mousewheel)
        
        # Build control sections
        self.build_banner_section()
        self.build_color_section()
        self.build_animation_section()
        self.build_canvas_section()
        self.build_export_section()
        
        # Right panel (preview)
        right_panel = ttk.Frame(main_container, style='Secondary.TFrame')
        right_panel.pack(side='right', fill='both', expand=True)
        
        self.build_preview_section(right_panel)
        
    def create_section(self, parent, title, icon=""):
        """Create a styled section card."""
        t = self.theme
        
        # Card container
        card = tk.Frame(parent, bg=t['bg_secondary'], 
            highlightbackground=t['border'], highlightthickness=1)
        card.pack(fill='x', pady=(0, 10))
        
        # Section header
        header = tk.Frame(card, bg=t['bg_secondary'])
        header.pack(fill='x', padx=12, pady=(10, 5))
        
        tk.Label(header, text=f"{icon} {title}",
            bg=t['bg_secondary'], fg=t['section_header'],
            font=('Segoe UI', 11, 'bold')).pack(side='left')
        
        # Content frame
        content = ttk.Frame(card, style='Secondary.TFrame')
        content.pack(fill='x', padx=12, pady=(0, 12))
        
        return content
        
    def build_banner_section(self):
        """Build the Banner Content section."""
        content = self.create_section(self.controls_frame, "BANNER CONTENT", "▶")
        
        # Text input
        ttk.Label(content, text="Banner Text").pack(anchor='w')
        self.text_var = tk.StringVar(value=self.config['custom_text'])
        self.text_var.trace('w', self.update_config)
        text_entry = ttk.Entry(content, textvariable=self.text_var, width=45)
        text_entry.pack(fill='x', pady=(2, 10))
        
        # Threat level
        ttk.Label(content, text="Threat Level").pack(anchor='w')
        self.threat_var = tk.StringVar(value=self.config['threat_level'])
        self.threat_var.trace('w', self.update_config)
        threat_levels = [
            "Easy (0 skulls)", "Normal (1 skull)", "Hard (2 skulls)", "Overkill (3 skulls)",
            "Mayhem (4 skulls)", "Death Wish (5 skulls)", "Death Sentence (6 skulls)",
            "Juggernaut (7 skulls)", "Apocalypse (8 skulls)", "Cataclysmic (9 skulls)",
            "Armageddon (10 skulls)"
        ]
        threat_combo = ttk.Combobox(content, textvariable=self.threat_var,
            values=threat_levels, state='readonly', width=30)
        threat_combo.pack(fill='x', pady=(2, 0))
        
    def build_color_section(self):
        """Build the Color Scheme section."""
        t = self.theme
        content = self.create_section(self.controls_frame, "COLOR SCHEME", "◆")
        
        # Helper to convert hex to RGB and back
        def hex_to_rgb(hex_color):
            return tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        def rgb_to_hex(rgb):
            return '#{:02x}{:02x}{:02x}'.format(*rgb)
        
        def darken_color(hex_color, factor):
            """Darken a color by a factor (0.0 to 1.0)."""
            r, g, b = hex_to_rgb(hex_color)
            return rgb_to_hex((int(r * factor), int(g * factor), int(b * factor)))
        
        def create_color_row(parent, label, config_key, initial_color, is_bg=False):
            row = ttk.Frame(parent, style='Secondary.TFrame')
            row.pack(fill='x', pady=3)
            
            ttk.Label(row, text=label, width=12).pack(side='left')
            
            # Color swatch button
            btn = tk.Button(row, width=8, height=1,
                bg=initial_color, activebackground=initial_color,
                relief='solid', borderwidth=1,
                cursor='hand2')
            btn.pack(side='left', padx=(5, 10))
            
            # Hex label
            hex_lbl = tk.Label(row, text=initial_color,
                bg=t['bg_secondary'], fg=t['fg_dim'],
                font=('Consolas', 9))
            hex_lbl.pack(side='left')
            
            def choose():
                # If this is a BG color and auto_bg_color is enabled, don't allow choosing
                if is_bg and self.auto_bg_var.get():
                    messagebox.showinfo("Auto BG Enabled", 
                        "Disable 'Auto BG from Main' to manually set background colors.")
                    return
                    
                color = colorchooser.askcolor(color=self.config[config_key])[1]
                if color:
                    self.config[config_key] = color
                    btn.config(bg=color, activebackground=color)
                    hex_lbl.config(text=color)
                    
                    # If this is the main color and auto-BG is enabled, update BG colors
                    if config_key == 'color' and self.auto_bg_var.get():
                        self.auto_generate_bg_colors()
                    
                    self.renderer = BannerRenderer(self.config)
            
            btn.config(command=choose)
            return btn, hex_lbl, row
        
        # Main color row with auto-BG checkbox
        main_row = ttk.Frame(content, style='Secondary.TFrame')
        main_row.pack(fill='x', pady=3)
        
        ttk.Label(main_row, text="Main Color", width=12).pack(side='left')
        
        self.color_btn = tk.Button(main_row, width=8, height=1,
            bg=self.config['color'], activebackground=self.config['color'],
            relief='solid', borderwidth=1, cursor='hand2')
        self.color_btn.pack(side='left', padx=(5, 10))
        
        self.color_lbl = tk.Label(main_row, text=self.config['color'],
            bg=t['bg_secondary'], fg=t['fg_dim'], font=('Consolas', 9))
        self.color_lbl.pack(side='left')
        
        def choose_main_color():
            color = colorchooser.askcolor(color=self.config['color'])[1]
            if color:
                self.config['color'] = color
                self.color_btn.config(bg=color, activebackground=color)
                self.color_lbl.config(text=color)
                
                # If auto-BG is enabled, update BG colors
                if self.auto_bg_var.get():
                    self.auto_generate_bg_colors()
                
                self.renderer = BannerRenderer(self.config)
        
        self.color_btn.config(command=choose_main_color)
        
        # Auto-generate BG checkbox
        auto_row = ttk.Frame(content, style='Secondary.TFrame')
        auto_row.pack(fill='x', pady=(5, 3))
        
        self.auto_bg_var = tk.BooleanVar(value=self.config.get('auto_bg_color', True))
        auto_cb = ttk.Checkbutton(auto_row, text="Auto BG from Main",
            variable=self.auto_bg_var, command=self.on_auto_bg_toggle)
        auto_cb.pack(side='left')
        
        ttk.Label(auto_row, text="(auto-generates flicker colors)", 
            style='Dim.TLabel').pack(side='left', padx=(5, 0))
        
        # Background color rows
        self.bg_c1_btn, self.bg_c1_lbl, self.bg_c1_row = create_color_row(
            content, "BG Pulse A", 'bg_color_1', self.config['bg_color_1'], is_bg=True)
        self.bg_c2_btn, self.bg_c2_lbl, self.bg_c2_row = create_color_row(
            content, "BG Pulse B", 'bg_color_2', self.config['bg_color_2'], is_bg=True)
        
        # Apply initial auto-generate if enabled
        if self.auto_bg_var.get():
            self.auto_generate_bg_colors()
        self.update_bg_button_states()
    
    def auto_generate_bg_colors(self):
        """Generate background flicker colors from main color."""
        main_hex = self.config['color']
        
        # Convert to RGB
        r = int(main_hex[1:3], 16)
        g = int(main_hex[3:5], 16)
        b = int(main_hex[5:7], 16)
        
        # BG Pulse A: 80% brightness
        bg1_r = int(r * 0.80)
        bg1_g = int(g * 0.80)
        bg1_b = int(b * 0.80)
        
        # BG Pulse B: 40% brightness
        bg2_r = int(r * 0.40)
        bg2_g = int(g * 0.40)
        bg2_b = int(b * 0.40)
        
        bg1_hex = '#{:02x}{:02x}{:02x}'.format(bg1_r, bg1_g, bg1_b)
        bg2_hex = '#{:02x}{:02x}{:02x}'.format(bg2_r, bg2_g, bg2_b)
        
        self.config['bg_color_1'] = bg1_hex
        self.config['bg_color_2'] = bg2_hex
        
        # Update UI
        self.bg_c1_btn.config(bg=bg1_hex, activebackground=bg1_hex)
        self.bg_c1_lbl.config(text=bg1_hex)
        self.bg_c2_btn.config(bg=bg2_hex, activebackground=bg2_hex)
        self.bg_c2_lbl.config(text=bg2_hex)
        
        self.renderer = BannerRenderer(self.config)
    
    def on_auto_bg_toggle(self):
        """Handle auto-BG checkbox toggle."""
        self.config['auto_bg_color'] = self.auto_bg_var.get()
        if self.auto_bg_var.get():
            self.auto_generate_bg_colors()
        self.update_bg_button_states()
    
    def update_bg_button_states(self):
        """Enable/disable background color buttons based on auto-BG setting."""
        if self.auto_bg_var.get():
            # Disable buttons - make them look inactive
            self.bg_c1_btn.config(state='disabled', cursor='arrow')
            self.bg_c2_btn.config(state='disabled', cursor='arrow')
        else:
            # Enable buttons
            self.bg_c1_btn.config(state='normal', cursor='hand2')
            self.bg_c2_btn.config(state='normal', cursor='hand2')

    def build_animation_section(self):
        """Build the Animation section."""
        t = self.theme
        content = self.create_section(self.controls_frame, "ANIMATION", "⚡")
        
        # Start flicker checkbox
        self.flicker_var = tk.BooleanVar(value=self.config['start_flicker'])
        self.flicker_var.trace('w', self.update_config)
        flicker_cb = ttk.Checkbutton(content, text="Enable Start Flicker Animation",
            variable=self.flicker_var)
        flicker_cb.pack(anchor='w', pady=(0, 5))
        
        # Flicker duration slider
        flicker_dur_frame = ttk.Frame(content, style='Secondary.TFrame')
        flicker_dur_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(flicker_dur_frame, text="Flicker Duration (s)", width=16).pack(side='left')
        
        self.flicker_dur_var = tk.DoubleVar(value=self.config['start_flicker_duration'])
        self.flicker_dur_var.trace('w', self.update_config)
        
        flicker_dur_spin = ttk.Spinbox(flicker_dur_frame, from_=0.5, to=10.0,
            textvariable=self.flicker_dur_var, width=6, increment=0.5)
        flicker_dur_spin.pack(side='left', padx=(5, 0))
        
        self.flicker_dur_lbl = tk.Label(flicker_dur_frame, text="sec",
            bg=t['bg_secondary'], fg=t['fg_dim'],
            font=('Segoe UI', 9))
        self.flicker_dur_lbl.pack(side='left', padx=(5, 0))
        
        # Speed slider with value label
        speed_frame = ttk.Frame(content, style='Secondary.TFrame')
        speed_frame.pack(fill='x')
        
        ttk.Label(speed_frame, text="BG Flicker Speed").pack(anchor='w')
        
        slider_row = ttk.Frame(speed_frame, style='Secondary.TFrame')
        slider_row.pack(fill='x', pady=(2, 0))
        
        self.speed_var = tk.DoubleVar(value=self.config['bg_flicker_speed'])
        self.speed_var.trace('w', self.update_config)
        
        speed_slider = ttk.Scale(slider_row, from_=0.0, to=5.0,
            variable=self.speed_var, length=250)
        speed_slider.pack(side='left', fill='x', expand=True)
        
        self.speed_lbl = tk.Label(slider_row, text=f"{self.config['bg_flicker_speed']:.1f}x",
            bg=t['bg_secondary'], fg=t['accent'],
            font=('Consolas', 10, 'bold'), width=5)
        self.speed_lbl.pack(side='right', padx=(10, 0))
        
        # Update speed label when slider changes
        def update_speed_label(*args):
            try:
                self.speed_lbl.config(text=f"{self.speed_var.get():.1f}x")
            except:
                pass
        self.speed_var.trace('w', update_speed_label)
        
    def build_canvas_section(self):
        """Build the Canvas Settings section."""
        content = self.create_section(self.controls_frame, "CANVAS OUTPUT", "▣")
        
        # Width
        width_row = ttk.Frame(content, style='Secondary.TFrame')
        width_row.pack(fill='x', pady=(0, 8))
        
        ttk.Label(width_row, text="Width (px)", width=12).pack(side='left')
        self.width_var = tk.IntVar(value=self.config['canvas_width'])
        self.width_var.trace('w', self.update_config)
        width_spin = ttk.Spinbox(width_row, from_=300, to=4096,
            textvariable=self.width_var, width=10)
        width_spin.pack(side='left', padx=(5, 0))
        
        # Height mode
        ttk.Label(content, text="Height Mode").pack(anchor='w')
        mode_frame = ttk.Frame(content, style='Secondary.TFrame')
        mode_frame.pack(fill='x', pady=(2, 8))
        
        self.height_mode_var = tk.StringVar(value=self.config['canvas_height_mode'])
        self.height_mode_var.trace('w', self.update_config)
        
        ttk.Radiobutton(mode_frame, text="Fixed 1080p",
            variable=self.height_mode_var, value='fixed').pack(side='left', padx=(0, 15))
        ttk.Radiobutton(mode_frame, text="Fit to Banner",
            variable=self.height_mode_var, value='fit').pack(side='left')
        
        # Padding
        pad_row = ttk.Frame(content, style='Secondary.TFrame')
        pad_row.pack(fill='x')
        
        ttk.Label(pad_row, text="Fit Padding", width=12).pack(side='left')
        self.pad_var = tk.IntVar(value=self.config['fit_padding'])
        self.pad_var.trace('w', self.update_config)
        pad_spin = ttk.Spinbox(pad_row, from_=0, to=200,
            textvariable=self.pad_var, width=10)
        pad_spin.pack(side='left', padx=(5, 0))
        
    def build_export_section(self):
        """Build the Export section."""
        t = self.theme
        content = self.create_section(self.controls_frame, "EXPORT", "◤")
        
        # Format and FPS row
        row1 = ttk.Frame(content, style='Secondary.TFrame')
        row1.pack(fill='x', pady=(0, 8))
        
        ttk.Label(row1, text="Format", width=12).pack(side='left')
        self.format_var = tk.StringVar(value='mp4')
        format_combo = ttk.Combobox(row1, textvariable=self.format_var,
            values=['mp4', 'gif'], state='readonly', width=8)
        format_combo.pack(side='left', padx=(5, 20))
        
        ttk.Label(row1, text="FPS").pack(side='left')
        self.fps_var = tk.IntVar(value=60)
        fps_spin = ttk.Spinbox(row1, from_=24, to=144,
            textvariable=self.fps_var, width=6)
        fps_spin.pack(side='left', padx=(5, 0))
        
        # Duration row
        row2 = ttk.Frame(content, style='Secondary.TFrame')
        row2.pack(fill='x', pady=(0, 8))
        
        ttk.Label(row2, text="Duration (s)", width=12).pack(side='left')
        self.duration_var = tk.DoubleVar(value=5.0)
        dur_spin = ttk.Spinbox(row2, from_=0.5, to=300,
            textvariable=self.duration_var, width=8, increment=0.5)
        dur_spin.pack(side='left', padx=(5, 0))
        
        # Auto-calculate
        auto_frame = ttk.Frame(content, style='Secondary.TFrame')
        auto_frame.pack(fill='x', pady=(0, 12))
        
        self.auto_loop_var = tk.BooleanVar(value=False)
        auto_cb = ttk.Checkbutton(auto_frame, text="Auto-calc GIF loop duration",
            variable=self.auto_loop_var, command=self.update_est_duration)
        auto_cb.pack(side='left')
        
        self.est_dur_lbl = tk.Label(auto_frame, text="",
            bg=t['bg_secondary'], fg=t['fg_dim'],
            font=('Segoe UI', 9))
        self.est_dur_lbl.pack(side='right')
        
        # Export button (prominent)
        export_btn = ttk.Button(content, text="◢ EXPORT RENDER ◣",
            style='Accent.TButton', command=self.start_export)
        export_btn.pack(fill='x', pady=(5, 0))
        
    def build_preview_section(self, parent):
        """Build the Preview panel."""
        t = self.theme
        
        # Preview header
        header = tk.Frame(parent, bg=t['bg_secondary'])
        header.pack(fill='x', padx=15, pady=(15, 10))
        
        tk.Label(header, text="◆ LIVE PREVIEW",
            bg=t['bg_secondary'], fg=t['section_header'],
            font=('Segoe UI', 11, 'bold')).pack(side='left')
        
        # Replay button
        replay_btn = ttk.Button(header, text="↺ Replay",
            command=self.restart_anim)
        replay_btn.pack(side='right')
        
        # Preview canvas container
        preview_container = tk.Frame(parent, bg=t['border'])
        preview_container.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        
        self.preview_canvas = tk.Canvas(preview_container,
            bg=t['preview_bg'], highlightthickness=0)
        self.preview_canvas.pack(fill='both', expand=True, padx=2, pady=2)
        
    def toggle_theme(self):
        """Switch between dark and light themes."""
        self.current_theme = self.theme_var.get()
        self.theme = THEMES[self.current_theme]
        
        # Rebuild UI with new theme
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.setup_styles()
        self.build_ui()
        
    def update_config(self, *args):
        """Update configuration from UI variables."""
        self.config['custom_text'] = self.text_var.get()
        self.config['threat_level'] = self.threat_var.get()
        self.config['start_flicker'] = self.flicker_var.get()
        try:
            self.config['start_flicker_duration'] = self.flicker_dur_var.get()
        except: pass
        try:
            self.config['bg_flicker_speed'] = self.speed_var.get()
        except: pass
        try:
            self.config['canvas_width'] = self.width_var.get()
        except: pass
        self.config['canvas_height_mode'] = self.height_mode_var.get()
        try:
            self.config['fit_padding'] = self.pad_var.get()
        except: pass
        
        self.renderer = BannerRenderer(self.config)
        self.update_est_duration()

    def update_est_duration(self):
        """Update the estimated duration label based on animation settings."""
        if self.auto_loop_var.get():
            loop_dur = self.renderer.estimate_loop_duration()
            
            if self.config['start_flicker']:
                # With intro animation: need flicker duration + expand animation + loop
                flicker_dur = self.config.get('start_flicker_duration', 2.0)
                expand_dur = 0.45  # Banner expand animation duration
                total = flicker_dur + expand_dur + loop_dur
                hint = f"≈ {total:.2f}s (intro + loop)"
            else:
                # No intro animation: just the loop duration for seamless looping
                total = loop_dur
                hint = f"≈ {total:.2f}s (loop only)"
            
            self.est_dur_lbl.config(text=hint)
            self.duration_var.set(round(total, 2))
        else:
            self.est_dur_lbl.config(text="")

    def restart_anim(self):
        """Restart the preview animation."""
        self.start_time = time.time()

    def animate_preview(self):
        """Animate the preview canvas."""
        if not self.preview_running:
            return
        
        try:
            elapsed = time.time() - self.start_time
            w = self.config.get('canvas_width', 1920)
            hm = self.config.get('canvas_height_mode', 'fixed')
            pad = self.config.get('fit_padding', 50)
            
            pil_img = self.renderer.draw_frame(elapsed, w, hm, 0, pad)
            
            # Scale to fit preview canvas
            canvas_w = self.preview_canvas.winfo_width()
            canvas_h = self.preview_canvas.winfo_height()
            if canvas_w < 10: canvas_w = 800
            if canvas_h < 10: canvas_h = 500
            
            pil_img.thumbnail((canvas_w - 20, canvas_h - 20))
            
            self.tk_img = ImageTk.PhotoImage(pil_img)
            self.preview_canvas.delete("all")
            
            self.preview_canvas.create_image(
                canvas_w // 2, canvas_h // 2, 
                image=self.tk_img)
        except Exception as e:
            pass  # Silently ignore errors during animation
            
        self.root.after(33, self.animate_preview)

    def start_export(self):
        """Start the export process."""
        fmt = self.format_var.get()
        
        # Ensure exports directory exists
        if not os.path.isdir(EXPORTS_DIR):
            try:
                os.makedirs(EXPORTS_DIR, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Export Error", f"Could not create exports folder:\n{e}")
                return
        
        # Generate auto-filename suggestion
        auto_filename = generate_export_filename(self.config['custom_text'], fmt)
        default_path = os.path.join(EXPORTS_DIR, auto_filename)
        
        file_types = [("MP4 Video", "*.mp4")] if fmt == 'mp4' else [("GIF Image", "*.gif")]
        filename = filedialog.asksaveasfilename(
            initialdir=EXPORTS_DIR,
            initialfile=auto_filename,
            defaultextension=f".{fmt}",
            filetypes=file_types
        )
        
        if not filename:
            return
        
        duration = self.duration_var.get()
        fps = self.fps_var.get()
        total_frames = int(duration * fps)
        
        w = self.config.get('canvas_width', 1920)
        hm = self.config.get('canvas_height_mode', 'fixed')
        pad = self.config.get('fit_padding', 50)
        
        t = self.theme
        
        # Create progress dialog
        top = tk.Toplevel(self.root)
        top.title("Exporting...")
        top.geometry("350x120")
        top.configure(bg=t['bg_secondary'])
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()
        
        tk.Label(top, text="◢ RENDERING IN PROGRESS ◣",
            bg=t['bg_secondary'], fg=t['accent'],
            font=('Segoe UI', 12, 'bold')).pack(pady=(20, 10))
        
        progress = ttk.Progressbar(top, length=280, mode='determinate', maximum=total_frames)
        progress.pack(pady=10)
        
        frame_lbl = tk.Label(top, text=f"0 / {total_frames} frames",
            bg=t['bg_secondary'], fg=t['fg_dim'],
            font=('Segoe UI', 9))
        frame_lbl.pack()
        
        self.root.update()
        
        def run_render():
            try:
                frames = []
                for i in range(total_frames):
                    t_sec = i / fps
                    img = self.renderer.draw_frame(t_sec, w, hm, 0, pad)
                    
                    if fmt == 'mp4':
                        bg = Image.new("RGB", img.size, (0, 0, 0))
                        bg.paste(img, mask=img.split()[3])
                        open_cv_image = np.array(bg) 
                        open_cv_image = open_cv_image[:, :, ::-1].copy() 
                        frames.append(open_cv_image)
                    else:
                        frames.append(img)
                    
                    progress['value'] = i + 1
                    frame_lbl.config(text=f"{i + 1} / {total_frames} frames")
                    top.update()
                    
                if fmt == 'mp4':
                    h, width = frames[0].shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    out = cv2.VideoWriter(filename, fourcc, fps, (width, h))
                    for f in frames:
                        out.write(f)
                    out.release()
                else:
                    # GIF Export
                    safe_fps = min(fps, 50) 
                    frame_dur = int(1000 / safe_fps)
                    
                    frames[0].save(
                        filename,
                        save_all=True,
                        append_images=frames[1:],
                        loop=0,
                        duration=frame_dur,
                        disposal=2 
                    )
                    
                messagebox.showinfo("Export Complete", f"Successfully exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))
            finally:
                top.destroy()
                
        threading.Thread(target=run_render).start()


if __name__ == "__main__":
    # Check for required folders before starting
    success, error_msg = check_required_folders()
    
    if not success:
        # Show error dialog and exit
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        messagebox.showerror("Startup Error", error_msg)
        root.destroy()
        sys.exit(1)
    
    root = tk.Tk()
    app = PaydayApp(root)
    root.mainloop()
