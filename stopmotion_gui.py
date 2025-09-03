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
import numpy as np
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

def find_typical_frame(selected_df, sample_size=10):
    """
    Find a typical frame by analyzing edge feature matches across multiple images.
    Uses edge detection to ensure consistency between day/night images.
    Returns the index of the image that has the most edge matches with other images.
    """
    total_images = len(selected_df)
    if total_images <= 1:
        return 0
    
    # Sample a subset of images for efficiency
    step = max(1, total_images // sample_size)
    sample_indices = list(range(0, total_images, step))
    
    orb = cv2.ORB_create(500)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    
    best_score = 0
    best_idx = 0
    
    for i in sample_indices:
        img_path = selected_df.iloc[i]['path']
        img = cv2.imread(img_path)
        if img is None:
            continue
            
        # Convert to grayscale and apply edge detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        kp, des = orb.detectAndCompute(edges, None)
        
        if des is None:
            continue
            
        total_matches = 0
        for j in sample_indices:
            if i == j:
                continue
                
            other_img_path = selected_df.iloc[j]['path']
            other_img = cv2.imread(other_img_path)
            if other_img is None:
                continue
                
            other_gray = cv2.cvtColor(other_img, cv2.COLOR_BGR2GRAY)
            other_edges = cv2.Canny(other_gray, 50, 150)
            other_kp, other_des = orb.detectAndCompute(other_edges, None)
            
            if other_des is None:
                continue
                
            matches = matcher.match(des, other_des)
            total_matches += len(matches)
        
        if total_matches > best_score:
            best_score = total_matches
            best_idx = i
    
    print(f"Selected frame {best_idx + 1} as reference (best edge match score: {best_score})")
    return best_idx

def validate_transformation(M, width, height, max_rotation=10, max_translation_pct=10, max_scale_change=10):
    """
    Validate if the transformation matrix is within acceptable limits.
    
    Args:
        M: 2x3 affine transformation matrix
        width, height: image dimensions
        max_rotation: maximum rotation in degrees
        max_translation_pct: maximum translation as percentage of image width
        max_scale_change: maximum scale change as percentage
    
    Returns:
        bool: True if transformation is valid, False otherwise
    """
    if M is None:
        return False
    
    # Extract rotation angle
    rotation_rad = np.arctan2(M[1, 0], M[0, 0])
    rotation_deg = np.abs(np.degrees(rotation_rad))
    
    # Extract scale
    scale_x = np.sqrt(M[0, 0]**2 + M[1, 0]**2)
    scale_y = np.sqrt(M[0, 1]**2 + M[1, 1]**2)
    scale_change_x = abs(scale_x - 1.0) * 100
    scale_change_y = abs(scale_y - 1.0) * 100
    
    # Extract translation
    translation_x = abs(M[0, 2])
    translation_y = abs(M[1, 2])
    translation_pct_x = (translation_x / width) * 100
    translation_pct_y = (translation_y / height) * 100
    
    # Check limits
    if rotation_deg > max_rotation:
        return False
    if scale_change_x > max_scale_change or scale_change_y > max_scale_change:
        return False
    if translation_pct_x > max_translation_pct or translation_pct_y > max_translation_pct:
        return False
    
    return True

def create_stopmotion_video(df: pd.DataFrame, location: str, since: datetime, until: datetime, fps=30, progress_callback=None):
    OUTPUT_PATH = "Z:/videos/stopmotion"
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    selected_df = filter_by_location_and_time(df, location, since, until)
    if selected_df.empty:
        print(f"No images found for location '{location}' between {since} and {until}.")
        return
    
    # Reset index to ensure proper indexing
    selected_df = selected_df.sort_values('timestamp').reset_index(drop=True)
    total_images = len(selected_df)
    
    if progress_callback:
        progress_callback("Finding optimal reference frame...", 0, total_images)
    
    # Find the most typical frame as reference
    ref_idx = find_typical_frame(selected_df)
    ref_img_path = selected_df.iloc[ref_idx]['path']
    ref_img = cv2.imread(ref_img_path)
    
    if ref_img is None:
        print(f"Error: Could not read reference image {ref_img_path}")
        return
        
    height, width = ref_img.shape[:2]
    gray_ref = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
    
    # Use edge detection for consistent feature matching between day/night
    edges_ref = cv2.Canny(gray_ref, 50, 150)
    
    # Feature detector for image alignment
    orb = cv2.ORB_create(500)
    
    # Detect keypoints and descriptors in reference edge image
    kp_ref, des_ref = orb.detectAndCompute(edges_ref, None)
    
    if des_ref is None:
        print("Warning: No edge features detected in reference image. Proceeding without alignment.")
        use_alignment = False
    else:
        use_alignment = True

    # Setup video writers
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_path = os.path.join(OUTPUT_PATH, f"{location}_{since.strftime('%Y%m%d_%H%M%S')}_{until.strftime('%Y%m%d_%H%M%S')}.mp4")
    edges_video_path = os.path.join(OUTPUT_PATH, f"{location}_{since.strftime('%Y%m%d_%H%M%S')}_{until.strftime('%Y%m%d_%H%M%S')}_edges.mp4");
    
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
    out_edges = cv2.VideoWriter(edges_video_path, fourcc, fps, (width, height))

    processed_count = 0
    aligned_count = 0
    skipped_count = 0
    
    for i, (_, row) in enumerate(selected_df.iterrows()):
        if progress_callback:
            progress_callback(f"Processing image {i+1}/{total_images}...", i, total_images)
        
        img = cv2.imread(row['path'])
        if img is not None:
            aligned_img = img
            
            # Convert to grayscale and detect edges
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges_img = cv2.Canny(gray_img, 50, 150)
            
            # Convert edges to 3-channel for video output
            edges_colored = cv2.cvtColor(edges_img, cv2.COLOR_GRAY2BGR)
            
            if i == ref_idx:
                # For reference frame, overlay original image with transparency
                edges_with_ref = cv2.addWeighted(img, 0.7, edges_colored, 0.3, 0)
                out_edges.write(edges_with_ref)
            else:
                out_edges.write(edges_colored)
            
            if use_alignment and i != ref_idx:  # Skip alignment for reference image
                try:
                    kp, des = orb.detectAndCompute(edges_img, None)
                    
                    if des is not None:
                        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                        matches = matcher.match(des, des_ref)
                        matches = sorted(matches, key=lambda x: x.distance)
                        
                        if len(matches) > 15:  # Increased minimum matches for better reliability
                            src_pts = np.float32([kp[m.queryIdx].pt for m in matches]).reshape(-1,1,2)
                            dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in matches]).reshape(-1,1,2)
                            
                            # Use affine transformation for alignment
                            M, _ = cv2.estimateAffinePartial2D(src_pts, dst_pts)
                            
                            # Validate transformation limits
                            if validate_transformation(M, width, height):
                                aligned_img = cv2.warpAffine(img, M, (width, height))
                                aligned_count += 1
                            else:
                                print(f"Warning: Transformation rejected for image {i+1} (outside limits)")
                                skipped_count += 1
                        else:
                            print(f"Warning: Not enough edge matches for alignment in image {i+1} ({len(matches)} matches)")
                            skipped_count += 1
                    else:
                        print(f"Warning: No edge features detected in image {i+1}")
                        skipped_count += 1
                        
                except Exception as e:
                    print(f"Warning: Edge-based alignment failed for image {i+1}: {e}")
                    skipped_count += 1
            
            out.write(aligned_img)
            processed_count += 1
        else:
            print(f"Warning: Could not read image {row['path']}.")
    
    out.release()
    out_edges.release()
    
    if progress_callback:
        progress_callback("Video creation complete!", total_images, total_images)
    
    print(f"Main video created: {video_path}")
    print(f"Edge debug video created: {edges_video_path}")
    print(f"Processed {processed_count} of {total_images} images")
    print(f"Reference frame: {ref_idx + 1}")
    if use_alignment:
        print(f"Successfully aligned: {aligned_count} images")
        print(f"Skipped alignment: {skipped_count} images (outside limits or insufficient features)")
        print("Edge-based image alignment was applied to handle day/night variations")


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

        # Limit to 1 image per day checkbox
        self.limit_per_day_var = tk.BooleanVar(value=False)
        self.limit_per_day_checkbox = tk.Checkbutton(master, text="Limit to 1 image per day (closest to noon)",
                                                    variable=self.limit_per_day_var, onvalue=True, offvalue=False)
        self.limit_per_day_checkbox.pack(pady=(0, 10))

        self.create_button = tk.Button(master, text="Create Video", command=self.create_video, 
                                      bg='green', fg='white', font=('Arial', 12, 'bold'))
        self.create_button.pack(pady=30)

        # Progress section (initially hidden)
        self.progress_frame = tk.Frame(master)
        
        self.progress_label = tk.Label(self.progress_frame, text="", 
                                      font=('Arial', 10), fg='blue')
        self.progress_label.pack(pady=(10, 5))
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, length=400, mode='determinate')
        self.progress_bar.pack(pady=5)
        
        self.progress_detail = tk.Label(self.progress_frame, text="", 
                                       font=('Arial', 9), fg='gray')
        self.progress_detail.pack(pady=(5, 10))

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
            # Optionally filter to 1 image per day (closest to noon)
            if self.limit_per_day_var.get():
                location_df = df[df['location'] == location].sort_values('timestamp')
                filtered_df = self.filter_one_per_day(location_df)
                self.current_location_timestamps = filtered_df['timestamp'].tolist()
                self.current_location_paths = filtered_df['path'].tolist()
            else:
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

    def update_progress(self, message, current, total):
        """Update progress bar and status message"""
        self.progress_label.config(text=message)
        
        if total > 0:
            progress_percent = (current / total) * 100
            self.progress_bar['value'] = progress_percent
            self.progress_detail.config(text=f"Progress: {current}/{total} ({progress_percent:.1f}%)")
        else:
            self.progress_bar['value'] = 0
            self.progress_detail.config(text="")
        
        # Force GUI update
        self.master.update_idletasks()

    def show_progress(self):
        """Show the progress section"""
        self.progress_frame.pack(pady=10, before=self.create_button)
        
    def hide_progress(self):
        """Hide the progress section"""
        self.progress_frame.pack_forget()

    def filter_one_per_day(self, df):
        """Return a DataFrame with only the image closest to noon for each day."""
        if df.empty:
            return df
        # Add a column for the time difference from noon
        noon = pd.to_datetime('12:00:00').time()
        df = df.copy()
        df['date'] = df['timestamp'].dt.date
        df['noon_diff'] = df['timestamp'].dt.time.apply(lambda t: abs((datetime.combine(datetime.min, t) - datetime.combine(datetime.min, noon)).total_seconds()))
        # For each day, keep the row with the smallest noon_diff
        filtered = df.loc[df.groupby('date')['noon_diff'].idxmin()].sort_values('timestamp').reset_index(drop=True)
        return filtered

    def create_video(self):
        # Disable button to prevent multiple simultaneous creations
        self.create_button.config(state='disabled', text='Creating Video...')
        self.show_progress()
        self.update_progress("Initializing...", 0, 100)
        
        try:
            selected_location = self.location_var.get()
            if not selected_location:
                messagebox.showerror("Error", "Please select a location.")
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
                # Create video with progress callback
                # If limiting per day, pass filtered DataFrame to video function
                if self.limit_per_day_var.get():
                    filtered_df = self.filter_one_per_day(df[df['location'] == location].sort_values('timestamp'))
                    create_stopmotion_video(filtered_df, location, since, until, fps, self.update_progress)
                else:
                    create_stopmotion_video(df, location, since, until, fps, self.update_progress)
                selected_count = until_idx - since_idx + 1
                
                self.update_progress("Complete!", selected_count, selected_count)
                
                # Show success message
                messagebox.showinfo("Success", f"Videos created successfully!\n"
                                  f"Location: {location}\n"
                                  f"Pictures used: {selected_count}\n"
                                  f"FPS: {fps}\n"
                                  f"Features: Edge-based alignment for day/night consistency\n"
                                  f"Output: Main video + Edge debug video")
                
                # Open Windows Explorer to the output folder
                output_path = "Z:\\videos\\stopmotion"
                # Ensure the directory exists
                os.makedirs(output_path, exist_ok=True)
                
                try:
                    # Use Windows path format to open explorer
                    subprocess.run(['explorer', output_path], check=True)
                except Exception as e:
                    print(f"Could not open explorer: {e}")
                    # Don't show error to user for explorer issues
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create video: {str(e)}")
                
        finally:
            # Re-enable button regardless of success or failure
            self.create_button.config(state='normal', text='Create Video')
            # Hide progress after a short delay
            self.master.after(2000, self.hide_progress)
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1800x2500")
    gui = StopmotionGUI(root)
    root.mainloop()