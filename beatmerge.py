import streamlit as st
import os
import tempfile
import subprocess
import math

# MoviePy Imports for BeatMerge
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, ColorClip
import moviepy.video.fx as vfx

# Import functions from your attached file
# Ensure Hrslooping.py is in the same folder
from Hrslooping import get_video_duration, fast_duplicate_video_by_hours

# --- Page Config ---
st.set_page_config(page_title="Custom Video Toolkit", page_icon="🎬", layout="wide")

# --- Sidebar Navigation ---
with st.sidebar:
    st.title("🛠️ Video Tools")
    # This menu allows you to join all custom tools in one window
    choice = st.radio("Select a Tool:", ["🎵 BeatMerge", "♾️ Fast Hours Looper"])
    st.divider()
    st.info("Switch between tools to process your videos.")

# --- TOOL 1: BeatMerge Logic ---
if choice == "🎵 BeatMerge":
    st.title("BeatMerge")
    st.write("Merge multiple video clips with any audio file — videos match audio length.")

    # UI Layout based on your image
    folder_path = st.text_input("Server folder path containing video clips", value="clip")
    audio_file = st.file_uploader("Choose audio file (mp3, wav, etc.)", type=["mp3", "wav"])
    transition_len = st.number_input("Transition length (seconds)", value=1.0, min_value=0.0, step=0.1)

    start_merge = st.button("Start Merge", type="primary")
    st.divider()

    st.subheader("Overlay Badge (kids)")
    enable_badge = st.checkbox("Enable animated badge", value=True)

    if enable_badge:
        r1 = st.columns([2, 1, 1, 1, 1, 1])
        with r1[0]: badge_text = st.text_input("Text", value="Subscribe!")
        with r1[1]: text_color = st.color_picker("Text color", "#E0E0E0")
        with r1[2]: box_color = st.color_picker("Box color", "#3F3075")
        with r1[3]: font_size = st.number_input("Size", value=21)
        with r1[4]: sparkle = st.checkbox("Sparkle overlay")
        with r1[5]: side_cover = st.checkbox("Side-cover (blurred sides)")

    if start_merge and audio_file:
        if not os.path.exists(folder_path):
            st.error(f"Error: Folder '{folder_path}' does not exist.")
        else:
            with st.spinner("🎬 Processing BeatMerge..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
                    tmp_audio.write(audio_file.getbuffer())
                    audio_path = tmp_audio.name
                
                audio = AudioFileClip(audio_path)
                total_duration = audio.duration
                video_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.mp4', '.mov', '.avi'))]
                
                if not video_files:
                    st.error("No video clips found.")
                else:
                    processed_clips = []
                    for v in video_files:
                        clip = VideoFileClip(v).without_audio()
                        if side_cover:
                            bg = clip.with_effects([vfx.Resize(width=1280), vfx.GaussianBlur(sigma=10), vfx.MultiplyColor(0.6)])
                            fg = clip.with_effects([vfx.Resize(height=720)])
                            clip = CompositeVideoClip([bg.with_position("center"), fg.with_position("center")], size=(1280, 720))
                        else:
                            clip = clip.with_effects([vfx.Resize(height=720)])
                        processed_clips.append(clip)

                    merged = concatenate_videoclips(processed_clips, method="compose", padding=-transition_len)
                    final_video = merged.with_effects([vfx.Loop(duration=total_duration)])
                    final_video = final_video.with_audio(audio)
                    layers = [final_video]

                    if sparkle:
                        sparkle_overlay = ColorClip(size=final_video.size, color=(255,255,255), duration=total_duration)
                        sparkle_overlay = sparkle_overlay.with_opacity(0.1).with_effects([vfx.Blink(d_on=0.1, d_off=0.3)])
                        layers.append(sparkle_overlay)

                    if enable_badge:
                        badge = (TextClip(text=badge_text, font_size=font_size, color=text_color, bg_color=box_color)
                                 .with_duration(total_duration).with_position(("center", 0.8), relative=True))
                        layers.append(badge)

                    result = CompositeVideoClip(layers)
                    output_fn = "merged_video.mp4"
                    result.write_videofile(output_fn, fps=24, codec="libx264")
                    st.success("Done!")
                    st.video(output_fn)

# --- TOOL 2: Fast Hours Looper Logic ---
elif choice == "♾️ Fast Hours Looper":
    st.title("Fast Hours Looper")
    st.write("Rapidly duplicate a video to reach a target duration (hours) using FFmpeg stream copy.")

    video_input = st.text_input("Input Video Name", value="merged_video.mp4")
    video_output = st.text_input("Output Video Name", value="BoneFire.mp4")
    target_hrs = st.number_input("Target Duration (Hours)", value=10, min_value=1)

    if st.button("Start Fast Looping", type="primary"):
        if not os.path.exists(video_input):
            st.error(f"Error: {video_input} not found! Run BeatMerge first or check the filename.")
        else:
            with st.spinner(f"Creating {target_hrs} hour video..."):
                # Calling logic from your Hrslooping.py file
                fast_duplicate_video_by_hours(video_input, video_output, target_hrs)
                st.success(f"Processing Complete! File saved as: {video_output}")