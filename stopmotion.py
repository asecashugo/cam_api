import os
import cv2
import datetime

def create_stopmotion_video(input_folder, fps=30):
    """
    Create a stop-motion video from images in the specified folder.
    
    :param input_folder: Folder containing the images.
    :param fps: Frames per second for the output video.
    """

    pictures_folder=input_folder+'/pictures'

    images = [img for img in os.listdir(pictures_folder) if img.endswith(('.png', '.jpg', '.jpeg'))]
    images.sort()  # Sort images to maintain order
    # guess start timestamp from the first image name
    if images:
        first_image_name = images[0]
        last_image_name = images[-1]

        start_timestamp_str = first_image_name.split('.')[0]  # Assuming format like '20250702_140322.jpg'
        start_timestamp = datetime.datetime.strptime(start_timestamp_str, '%Y%m%d_%H%M%S')
        print(f"Start timestamp: {start_timestamp}")

        last_timestamp_str = last_image_name.split('.')[0]
        last_timestamp = datetime.datetime.strptime(last_timestamp_str, '%Y%m%d_%H%M%S')
        print(f"Last timestamp: {last_timestamp}")
        duration = int((last_timestamp - start_timestamp).total_seconds())
        duration_unit='s'
        if duration > 3600:
            duration /= 3600
            print(f"Duration in hours: {duration} hours")
            duration=int(duration)
            duration_unit='h'
        elif duration > 60:
            duration/=60
            print(f"Duration in minutes: {duration} minutes")
            duration=int(duration)
            duration_unit='m'
        else:
            print(f"Duration of the video: {duration} seconds")        

    if not images:
        print("No images found in the specified folder.")
        return

    first_image_path = os.path.join(pictures_folder, images[0])
    frame = cv2.imread(first_image_path)
    height, width, layers = frame.shape

    video_path = os.path.join(input_folder, f'{input_folder.split('/')[-1]}_{duration}{duration_unit}.mp4')
    # if video_path exists, remove it
    if os.path.exists(video_path):
        os.remove(video_path)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4 format
    video = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    progress=0
    for image in images:
        progress += 1
        print(f'Processing image: {progress}/{len(images)}', end='\r')
        image_path = os.path.join(pictures_folder, image)
        frame = cv2.imread(image_path)
        if frame is not None:
            video.write(frame)

    video.release()
    print(f"Stop-motion video created at {video_path}")