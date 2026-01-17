import os
import subprocess
import math

def get_video_duration(input_file):
    """Video ki total duration seconds mein nikalne ke liye."""
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{input_file}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return None

def fast_duplicate_video_by_hours(input_file, output_file, target_hours):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} nahi mili!")
        return

    # 1. Video ki duration check karna
    duration_seconds = get_video_duration(input_file)
    if not duration_seconds:
        print("Video ki duration maloom nahi ho saki. FFmpeg/FFprobe check karein.")
        return

    # 2. Calculation: Kitni copies chahiye
    target_seconds = target_hours * 3600
    copy_count = math.ceil(target_seconds / duration_seconds)
    
    actual_duration_hrs = (copy_count * duration_seconds) / 3600

    print(f"Original Video Length: {duration_seconds:.2f} seconds")
    print(f"Target: {target_hours} hours")
    print(f"Zaroori Copies: {copy_count}")
    print(f"Final Video Duration takreeban {actual_duration_hrs:.2f} hours hogi.")

    # 3. List file banana
    list_file = "temp_list.txt"
    with open(list_file, "w") as f:
        abs_path = os.path.abspath(input_file).replace('\\', '/')
        for _ in range(copy_count):
            f.write(f"file '{abs_path}'\n")

    # 4. FFmpeg Command
    print("\nProcessing shuru hai... please intezar karein.")
    command = f'ffmpeg -f concat -safe 0 -i {list_file} -c copy "{output_file}" -y'

    try:
        result = subprocess.run(command, shell=True)
        if result.returncode == 0:
            print(f"\nKaam ho gaya! File yahan hai: {output_file}")
        else:
            print("FFmpeg mein koi masla aya.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)

# --- Settings ---
video_input = "merged.mp4"      # Aapki asli file
video_output = "BoneFire.mp4"   # Jo file banegi
target_hrs = 10                # Jitne ghante ki video chahiye

fast_duplicate_video_by_hours(video_input, video_output, target_hrs)