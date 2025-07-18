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
        data.append({'timestamp': timestamp, 'location': location})

df = pd.DataFrame(data)

df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y%m%d_%H%M%S')

summary_df = df.groupby('location').agg(
    picture_count=('timestamp', 'size'),
    since=('timestamp', 'min'),
    until=('timestamp', 'max')
).reset_index()

print(summary_df)