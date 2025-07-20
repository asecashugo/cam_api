PATH="Z:/pictures/cam_api"

import os

file_count = len([f for f in os.listdir(PATH) if os.path.isfile(os.path.join(PATH, f))])

file_names = [f for f in os.listdir(PATH) if os.path.isfile(os.path.join(PATH, f))]

import pandas as pd

data = []
for fname in file_names:
    if fname.endswith('.jpg'):
        parts = fname[:-4].split('_')
        timestamp = f"{parts[0]}_{parts[1]}"
        location = '_'.join(parts[2:])
        data.append({'timestamp': timestamp, 'location': location, 'path': os.path.join(PATH, fname)})

df = pd.DataFrame(data)

df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y%m%d_%H%M%S')

summary_df = df.groupby('location').agg(
    picture_count=('timestamp', 'size'),
    since=('timestamp', 'min'),
    until=('timestamp', 'max')
).reset_index()

import cv2
from datetime import datetime

def filter_by_location_and_time(df: pd.DataFrame, location: str, since: datetime, until: datetime) -> pd.DataFrame:
    """
    Filters the DataFrame for a specific location and time range.
    
    :param df: DataFrame containing image data.
    :param location: Location to filter by.
    :param since: Start datetime for filtering.
    :param until: End datetime for filtering.
    :return: Filtered DataFrame sorted by timestamp.
    """
    filtered_df = df[(df['location'] == location) & (df['timestamp'] >= since) & (df['timestamp'] <= until)]
    return filtered_df.sort_values('timestamp')

def create_stopmotion_video(df:pd.DataFrame, location:str, since:datetime, until:datetime, fps=30):
    OUTPUT_PATH= "Z:/videos/stopmotion"
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    selected_df = filter_by_location_and_time(df, location, since, until)
    if selected_df.empty:
        print(f"No images found for location '{location}' between {since} and {until}.")
        return
    
    # Ensure the DataFrame is sorted by timestamp (redundant safety check)
    selected_df = selected_df.sort_values('timestamp')
    
    first_img_path = selected_df.iloc[0]['path']
    first_img = cv2.imread(first_img_path)
    height, width = first_img.shape[:2]

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(os.path.join(OUTPUT_PATH, f"{location}_{since.strftime('%Y%m%d_%H%M%S')}_{until.strftime('%Y%m%d_%H%M%S')}.mp4"), fourcc, fps, (width, height))

    for _, row in selected_df.iterrows():
        img = cv2.imread(row['path'])
        if img is not None:
            out.write(img)
        else:
            print(f"Warning: Could not read image {row['path']}.")
    out.release()


# test
# create_stopmotion_video(df, location='skyline', since=pd.Timestamp('2023-01-01'), until=pd.Timestamp('2027-01-31'), fps=3)

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime, timedelta
import numpy as np
import subprocess
from PIL import Image, ImageTk
import os

class StopmotionGUI:
    def __init__(self, master):
        self.master = master
        master.title("Stopmotion Video Creator")

        # Calculate overall date range
        self.overall_min_date = summary_df['since'].min()
        self.overall_max_date = summary_df['until'].max()
        
        # Initialize current location data
        self.current_location_timestamps = []
        self.current_location_paths = []  # Store image paths
        self.current_location = None

        self.label = tk.Label(master, text="Select Location:")
        self.label.pack(pady=10)

        # Create location options with picture counts
        location_options = []
        for _, row in summary_df.iterrows():
            location_options.append(f"{row['location']} ({row['picture_count']} pictures)")
        
        self.location_var = tk.StringVar()
        self.location_dropdown = ttk.Combobox(master, textvariable=self.location_var, 
                                             values=location_options, state="readonly", width=50)
        self.location_dropdown.pack(pady=5)
        self.location_dropdown.bind('<<ComboboxSelected>>', self.on_location_selected)

        # Date range slider section
        self.date_range_frame = tk.Frame(master)
        self.date_range_frame.pack(pady=20, padx=20, fill='x')

        self.date_range_label = tk.Label(self.date_range_frame, text="Select Date Range:", font=('Arial', 12, 'bold'))
        self.date_range_label.pack(pady=(0, 10))

        # Create double slider
        self.slider_frame = tk.Frame(self.date_range_frame)
        self.slider_frame.pack(fill='x', pady=10)

        # Since slider
        self.since_label = tk.Label(self.slider_frame, text="From:")
        self.since_label.grid(row=0, column=0, sticky='w', padx=(0, 10))

        self.since_slider = tk.Scale(self.slider_frame, from_=0, to=1,
                                    orient=tk.HORIZONTAL, length=400, resolution=1,
                                    command=self.on_since_change, tickinterval=0, showvalue=0)
        self.since_slider.grid(row=0, column=1, sticky='ew', padx=5)

        # Until slider
        self.until_label = tk.Label(self.slider_frame, text="To:")
        self.until_label.grid(row=1, column=0, sticky='w', padx=(0, 10))

        self.until_slider = tk.Scale(self.slider_frame, from_=0, to=1,
                                    orient=tk.HORIZONTAL, length=400, resolution=1,
                                    command=self.on_until_change, tickinterval=0, showvalue=0)
        self.until_slider.grid(row=1, column=1, sticky='ew', padx=5)

        self.slider_frame.columnconfigure(1, weight=1)

        # Date display labels
        self.date_display_frame = tk.Frame(self.date_range_frame)
        self.date_display_frame.pack(fill='x', pady=10)

        self.since_date_label = tk.Label(self.date_display_frame, text="Please select a location first", 
                                        font=('Arial', 11), fg='blue')
        self.since_date_label.pack()

        self.until_date_label = tk.Label(self.date_display_frame, text="", 
                                        font=('Arial', 11), fg='blue')
        self.until_date_label.pack()

        # Picture count label
        self.picture_count_label = tk.Label(self.date_display_frame, text="", 
                                           font=('Arial', 10), fg='gray')
        self.picture_count_label.pack(pady=(10, 0))

        # FPS and duration section
        self.fps_frame = tk.Frame(self.date_range_frame)
        self.fps_frame.pack(fill='x', pady=10)

        self.fps_label = tk.Label(self.fps_frame, text="FPS (Frames Per Second):", 
                                 font=('Arial', 10, 'bold'))
        self.fps_label.pack()

        self.fps_entry = tk.Entry(self.fps_frame, width=10, justify='center')
        self.fps_entry.pack(pady=5)
        self.fps_entry.insert(0, "30")  # Default FPS
        self.fps_entry.bind('<KeyRelease>', self.on_fps_change)

        # Video duration label
        self.duration_label = tk.Label(self.fps_frame, text="", 
                                      font=('Arial', 10), fg='gray')
        self.duration_label.pack(pady=(5, 0))

        # Image preview section
        self.preview_frame = tk.Frame(self.date_range_frame)
        self.preview_frame.pack(fill='x', pady=20)

        # Since image preview
        self.since_preview_frame = tk.Frame(self.preview_frame)
        self.since_preview_frame.pack(side=tk.LEFT, padx=20, fill='both', expand=True)

        self.since_preview_label = tk.Label(self.since_preview_frame, text="Start Image:", 
                                           font=('Arial', 10, 'bold'))
        self.since_preview_label.pack()

        self.since_image_label = tk.Label(self.since_preview_frame, text="No image", 
                                         bg='lightgray')
        self.since_image_label.pack(pady=5)

        # Until image preview
        self.until_preview_frame = tk.Frame(self.preview_frame)
        self.until_preview_frame.pack(side=tk.RIGHT, padx=20, fill='both', expand=True)

        self.until_preview_label = tk.Label(self.until_preview_frame, text="End Image:", 
                                           font=('Arial', 10, 'bold'))
        self.until_preview_label.pack()

        self.until_image_label = tk.Label(self.until_preview_frame, text="No image", 
                                         bg='lightgray')
        self.until_image_label.pack(pady=5)

        self.create_button = tk.Button(master, text="Create Video", command=self.create_video, 
                                      bg='green', fg='white', font=('Arial', 12, 'bold'))
        self.create_button.pack(pady=30)

    def load_and_resize_image(self, image_path, max_width=600):
        """Load and resize an image for preview"""
        try:
            if not os.path.exists(image_path):
                return None
                
            # Open and resize image
            image = Image.open(image_path)
            
            # Calculate aspect ratio and resize
            aspect_ratio = image.height / image.width
            new_width = max_width
            new_height = int(new_width * aspect_ratio)
            
            # Resize image
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)
            return photo
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            return None

    def on_fps_change(self, event=None):
        """Handle FPS entry change and update duration"""
        self.update_duration_display()

    def update_duration_display(self):
        """Update the video duration display based on selected pictures and FPS"""
        if not self.current_location_timestamps:
            self.duration_label.config(text="")
            return
            
        try:
            fps = float(self.fps_entry.get())
            if fps <= 0:
                self.duration_label.config(text="FPS must be greater than 0")
                return
        except ValueError:
            self.duration_label.config(text="Please enter a valid FPS number")
            return
            
        since_idx = int(self.since_slider.get())
        until_idx = int(self.until_slider.get())
        selected_count = until_idx - since_idx + 1
        
        duration_seconds = selected_count / fps
        
        # Format duration nicely
        if duration_seconds < 60:
            duration_text = f"Video duration: {duration_seconds:.1f} seconds"
        else:
            minutes = int(duration_seconds // 60)
            seconds = duration_seconds % 60
            duration_text = f"Video duration: {minutes}m {seconds:.1f}s ({duration_seconds:.1f} total seconds)"
        
        self.duration_label.config(text=duration_text)

    def update_preview_images(self):
        """Update the preview images based on current slider positions"""
        if not self.current_location_paths:
            return
            
        since_idx = int(self.since_slider.get())
        until_idx = int(self.until_slider.get())
        
        # Update since image
        since_image_path = self.current_location_paths[since_idx]
        since_photo = self.load_and_resize_image(since_image_path)
        if since_photo:
            self.since_image_label.configure(image=since_photo, text="")
            self.since_image_label.image = since_photo  # Keep a reference
        else:
            self.since_image_label.configure(image="", text="Image not found")
            
        # Update until image
        until_image_path = self.current_location_paths[until_idx]
        until_photo = self.load_and_resize_image(until_image_path)
        if until_photo:
            self.until_image_label.configure(image=until_photo, text="")
            self.until_image_label.image = until_photo  # Keep a reference
        else:
            self.until_image_label.configure(image="", text="Image not found")

    def on_since_change(self, value):
        """Handle since slider change"""
        if not self.current_location_timestamps:
            return
            
        since_idx = int(float(value))
        until_idx = int(self.until_slider.get())
        
        # Ensure since is not after until
        if since_idx > until_idx:
            self.until_slider.set(since_idx)
        
        self.update_date_labels()
        self.update_preview_images()

    def on_until_change(self, value):
        """Handle until slider change"""
        if not self.current_location_timestamps:
            return
            
        until_idx = int(float(value))
        since_idx = int(self.since_slider.get())
        
        # Ensure until is not before since
        if until_idx < since_idx:
            self.since_slider.set(until_idx)
        
        self.update_date_labels()
        self.update_preview_images()

    def update_date_labels(self):
        """Update the date display labels"""
        if not self.current_location_timestamps:
            return
            
        since_idx = int(self.since_slider.get())
        until_idx = int(self.until_slider.get())
        
        since_datetime = self.current_location_timestamps[since_idx]
        until_datetime = self.current_location_timestamps[until_idx]
        
        self.since_date_label.config(text=f"From: {since_datetime.strftime('%Y-%m-%d %H:%M:%S')} (Picture {since_idx + 1})")
        self.until_date_label.config(text=f"To: {until_datetime.strftime('%Y-%m-%d %H:%M:%S')} (Picture {until_idx + 1})")
        
        # Update picture count
        selected_count = until_idx - since_idx + 1
        total_count = len(self.current_location_timestamps)
        self.picture_count_label.config(text=f"Selected: {selected_count} of {total_count} pictures")
        
        # Update duration display
        self.update_duration_display()

    def on_location_selected(self, event=None):
        """Update sliders when location is selected"""
        selected_location = self.location_var.get()
        if selected_location:
            location = selected_location.split(' (')[0]
            self.current_location = location
            
            # Get all timestamps and paths for this location, sorted
            location_df = df[df['location'] == location].sort_values('timestamp')
            self.current_location_timestamps = location_df['timestamp'].tolist()
            self.current_location_paths = location_df['path'].tolist()
            
            if self.current_location_timestamps:
                max_idx = len(self.current_location_timestamps) - 1
                
                # Update slider configurations to use picture indices
                self.since_slider.config(from_=0, to=max_idx)
                self.until_slider.config(from_=0, to=max_idx)
                
                # Set default values to the full range
                self.since_slider.set(0)
                self.until_slider.set(max_idx)
                
                self.update_date_labels()
                self.update_preview_images()
                self.update_duration_display()

    def create_video(self):
        selected_location = self.location_var.get()
        if not selected_location:
            messagebox.showerror("Error", "Please select a location.")
            return
            
        if not self.current_location_timestamps:
            messagebox.showerror("Error", "No pictures available for the selected location.")
            return
        
        # Extract location name from the dropdown selection (remove the picture count part)
        location = selected_location.split(' (')[0]
        
        # Get picture indices from sliders
        since_idx = int(self.since_slider.get())
        until_idx = int(self.until_slider.get())
        
        # Get the actual datetime objects from the selected picture indices
        since = self.current_location_timestamps[since_idx]
        until = self.current_location_timestamps[until_idx]
        
        # Add a small buffer to include the exact timestamps
        since = since - timedelta(seconds=1)
        until = until + timedelta(seconds=1)

        # Get FPS from entry field
        try:
            fps = float(self.fps_entry.get())
            if fps <= 0:
                messagebox.showerror("Error", "FPS must be greater than 0.")
                return
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid FPS number.")
            return

        try:
            create_stopmotion_video(df, location, since, until, fps)
            selected_count = until_idx - since_idx + 1
            
            # Open Windows Explorer to the output folder
            output_path = "Z:\\videos\\stopmotion"
            # Ensure the directory exists
            os.makedirs(output_path, exist_ok=True)
            
            try:
                # Use Windows path format and ensure it opens the correct folder
                subprocess.run(['explorer', output_path], check=True)
            except subprocess.CalledProcessError:
                try:
                    # Alternative method using /root flag
                    subprocess.run(['explorer', '/root,', output_path], check=True)
                except subprocess.CalledProcessError:
                    # Final fallback - open parent directory
                    parent_path = "Z:\\videos"
                    os.makedirs(parent_path, exist_ok=True)
                    subprocess.run(['explorer', parent_path], check=True)
            except Exception:
                pass  # Ignore explorer errors, don't let them break the success message
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create video: {str(e)}")
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1800x2500")
    gui = StopmotionGUI(root)
    root.mainloop()