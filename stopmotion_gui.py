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
    :return: Filtered DataFrame.
    """
    return df[(df['location'] == location) & (df['timestamp'] >= since) & (df['timestamp'] <= until)]

def create_stopmotion_video(df:pd.DataFrame, location:str, since:datetime, until:datetime, fps=30):
    OUTPUT_PATH= "Z:/videos/stopmotion"
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    selected_df = filter_by_location_and_time(df, location, since, until)
    if selected_df.empty:
        print(f"No images found for location '{location}' between {since} and {until}.")
        return
    
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
from datetime import datetime
from tkcalendar import DateEntry

class StopmotionGUI:
    def __init__(self, master):
        self.master = master
        master.title("Stopmotion Video Creator")

        # Calculate overall date range
        self.overall_min_date = summary_df['since'].min()
        self.overall_max_date = summary_df['until'].max()

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

        self.since_label = tk.Label(master, text="Since Date:")
        self.since_label.pack(pady=(20, 5))

        self.since_picker = DateEntry(master, width=20, background='darkblue',
                                     foreground='white', borderwidth=2,
                                     mindate=self.overall_min_date.date(),
                                     maxdate=self.overall_max_date.date(),
                                     date_pattern='yyyy-mm-dd')
        self.since_picker.pack(pady=5)

        self.until_label = tk.Label(master, text="Until Date:")
        self.until_label.pack(pady=(10, 5))

        self.until_picker = DateEntry(master, width=20, background='darkblue',
                                     foreground='white', borderwidth=2,
                                     mindate=self.overall_min_date.date(),
                                     maxdate=self.overall_max_date.date(),
                                     date_pattern='yyyy-mm-dd')
        self.until_picker.pack(pady=5)

        self.create_button = tk.Button(master, text="Create Video", command=self.create_video, 
                                      bg='green', fg='white', font=('Arial', 12, 'bold'))
        self.create_button.pack(pady=30)

    def on_location_selected(self, event=None):
        """Update date pickers when location is selected"""
        selected_location = self.location_var.get()
        if selected_location:
            location = selected_location.split(' (')[0]
            location_data = summary_df[summary_df['location'] == location].iloc[0]
            
            # Update date picker ranges to location-specific dates
            self.since_picker.config(mindate=location_data['since'].date(),
                                   maxdate=location_data['until'].date())
            self.until_picker.config(mindate=location_data['since'].date(),
                                   maxdate=location_data['until'].date())
            
            # Set default dates to the location's range
            self.since_picker.set_date(location_data['since'].date())
            self.until_picker.set_date(location_data['until'].date())

    def create_video(self):
        selected_location = self.location_var.get()
        if not selected_location:
            messagebox.showerror("Error", "Please select a location.")
            return
        
        # Extract location name from the dropdown selection (remove the picture count part)
        location = selected_location.split(' (')[0]
        
        # Get dates from date pickers
        since_date = self.since_picker.get_date()
        until_date = self.until_picker.get_date()
        
        # Convert dates to datetime objects (start of day for since, end of day for until)
        since = pd.to_datetime(since_date)
        until = pd.to_datetime(until_date) + pd.Timedelta(hours=23, minutes=59, seconds=59)
        
        # Validate date range
        if since > until:
            messagebox.showerror("Error", "Since date cannot be after Until date.")
            return

        try:
            create_stopmotion_video(df, location, since, until)
            messagebox.showinfo("Success", f"Video created successfully!\nLocation: {location}\nFrom: {since_date} to {until_date}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create video: {str(e)}")
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("600x600")
    gui = StopmotionGUI(root)
    root.mainloop()