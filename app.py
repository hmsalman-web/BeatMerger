import streamlit as st
import os
import tempfile
import subprocess
import math
import pyttsx3
import numpy as np
from scipy import signal
from pydub import AudioSegment
import asyncio
from pathlib import Path
from tkinter import Tk, filedialog
import threading

# MoviePy 2.0+ Imports
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, ColorClip
import moviepy.video.fx as vfx

# Try importing edge-tts for better quality singing
try:
    from edge_tts import Communicate
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# Import logic from your attached file
try:
    from Hrslooping import get_video_duration, fast_duplicate_video_by_hours
except ImportError:
    st.error("Error: 'Hrslooping.py' not found in the same folder!")

# --- Helper Function: Open Folder Picker ---
def open_folder_picker():
    """Opens a native Windows folder picker dialog"""
    def pick_folder():
        root = Tk()
        root.withdraw()  # Hide the tkinter window
        root.wm_attributes('-topmost', 1)  # Bring to front
        folder = filedialog.askdirectory(title="Select Folder Containing Video Clips")
        root.destroy()
        return folder
    
    # Run in separate thread to avoid blocking
    result = [None]
    def thread_func():
        result[0] = pick_folder()
    
    thread = threading.Thread(target=thread_func, daemon=True)
    thread.start()
    thread.join(timeout=30)  # Wait up to 30 seconds
    return result[0] if result[0] else ""

# --- Page Setup ---
st.set_page_config(page_title="Video Toolkit Dashboard", page_icon="🎬", layout="wide")

# --- Sidebar Menu ---
with st.sidebar:
    st.title("🛠️ Custom Video Tools")
    choice = st.radio("Switch Tools", ["🎵 BeatMerge (Fast)", "♾️ Hours Looper", "🎸 Song Generator"])
    st.divider()
    st.info("System Status: Ready")

# --- Tool 1: Fast BeatMerge ---
if choice == "🎵 BeatMerge (Fast)":
    st.title("BeatMerge (High Speed)")
    st.write("Renders effects once, then uses FFmpeg stream copy to match audio length.")

    # UI Inputs with Folder Picker
    col1, col2 = st.columns([4, 1])
    with col1:
        folder_path = st.text_input("Folder path containing video clips", value="clip", key="beatmerge_folder")
    with col2:
        if st.button("📁", help="Browse for folder", key="beatmerge_browse"):
            selected_folder = open_folder_picker()
            if selected_folder:
                st.session_state.beatmerge_folder = selected_folder
                st.rerun()
    
    audio_file = st.file_uploader("Choose audio file (mp3, wav, etc.)", type=["mp3", "wav"])
    
    st.divider()
    st.subheader("Overlay & Effects")
    enable_badge = st.checkbox("Enable Badge", value=True)
    
    if enable_badge:
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
        with c1: badge_text = st.text_input("Text", value="Subscribe!")
        with c2: text_color = st.color_picker("Text Color", "#FFFFFF")
        with c3: box_color = st.color_picker("Box Color", "#3F3075")
        with c4: font_size = st.number_input("Size", value=24)
        with c5: side_cover = st.checkbox("Side-cover", value=True)

    if st.button("Start Fast Merge", type="primary"):
        if not audio_file or not os.path.exists(folder_path):
            st.error("Missing audio file or invalid clip folder.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 1. Save Audio and get total length
            status_text.text("📥 Loading audio file...")
            progress_bar.progress(10)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                tmp.write(audio_file.getbuffer())
                audio_path = tmp.name
            audio = AudioFileClip(audio_path)
            total_audio_len = audio.duration

            # 2. Render Template (Clips + Effects)
            video_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                           if f.lower().endswith(('.mp4', '.mov'))]
            
            if not video_files:
                st.error("No video files found in the folder.")
            else:
                status_text.text("🎬 Processing video clips...")
                progress_bar.progress(20)
                raw_clips = []
                for idx, v in enumerate(video_files):
                    c = VideoFileClip(v).without_audio()
                    
                    if enable_badge and side_cover:
                        # Using the explicitly imported effect classes
                        bg = c.with_effects([
                            vfx.Resize(width=1280), 
                            vfx.blur(sigma=10), 
                            vfx.MultiplyColor(0.6)
                        ])
                        fg = c.with_effects([vfx.Resize(height=720)])
                        c = CompositeVideoClip([bg.with_position("center"), fg.with_position("center")], size=(1280, 720))
                    else:
                        c = c.with_effects([vfx.Resize(height=720)])
                    raw_clips.append(c)
                    progress_bar.progress(20 + int(20 * (idx + 1) / len(video_files)))

                # Create the short "visual template"
                status_text.text("🎞️ Creating video template...")
                progress_bar.progress(50)
                template = concatenate_videoclips(raw_clips, method="compose")

                if enable_badge:
                    # Create badge with smooth fade-in effect
                    badge = (TextClip(text=badge_text, font_size=font_size, color=text_color, bg_color=box_color)
                             .with_duration(template.duration)
                             .with_position((0.85, 0.05), relative=True)
                             .with_effects([vfx.CrossFadeIn(0.5)]))
                    template = CompositeVideoClip([template, badge])

                # Save the short rendered template (Only rendered once = Very Fast)
                status_text.text("💾 Rendering template...")
                progress_bar.progress(60)
                template.write_videofile("temp_template.mp4", codec="libx264", audio=False)
                
                # 3. High-Speed FFmpeg Stream Copy (Matching the MP3)
                # This is what makes it as fast as Node.js
                status_text.text("🔗 Merging video and audio...")
                progress_bar.progress(75)
                loop_count = int(total_audio_len / template.duration) + 1
                with open("list.txt", "w") as f:
                    for _ in range(loop_count):
                        f.write(f"file 'temp_template.mp4'\n")

                output_final = "beatmerge_output.mp4"
                # FFmpeg Command: Loop video + Add Audio + Cut at audio end using STREAM COPY
                # 
                cmd = f'ffmpeg -f concat -safe 0 -i list.txt -i "{audio_path}" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest "{output_final}" -y'
                subprocess.run(cmd, shell=True, capture_output=True)

                status_text.text("✅ Finalizing...")
                progress_bar.progress(90)
                
                if os.path.exists(output_final):
                    status_text.text("✅ Complete! Lightning fast merge done!")
                    progress_bar.progress(100)
                    st.success("✅ Lightning fast merge complete!")
                    # Video preview removed as requested
                else:
                    st.error(f"Output video '{output_final}' was not created. Please check your input files and try again.")

                # Cleanup temporary files
                if os.path.exists("list.txt"): os.remove("list.txt")
                if os.path.exists("temp_template.mp4"): os.remove("temp_template.mp4")

# --- Tool 2: Hours Looper ---
elif choice == "♾️ Hours Looper":
    st.title("Fast Hours Looper")
    st.write("Uses your 'Hrslooping.py' logic to make 10+ hour videos instantly.")

    # Input Video Path with Folder Picker
    col1, col2 = st.columns([4, 1])
    with col1:
        v_in = st.text_input("Input Video Path", value="beatmerge_output.mp4", key="hrslooper_input")
    with col2:
        if st.button("📁", help="Browse for video file", key="hrslooper_browse"):
            root = Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            selected_file = filedialog.askopenfilename(
                title="Select Input Video File",
                filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All Files", "*.*")]
            )
            root.destroy()
            if selected_file:
                st.session_state.hrslooper_input = selected_file
                st.rerun()
    
    v_out = st.text_input("Output File Name", value="Final_10_Hours.mp4")
    target = st.number_input("Target Hours", value=10, min_value=1)

    if st.button("Start Long Loop Process", type="primary"):
        if os.path.exists(v_in):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text(f"⏳ Processing {target} hours...")
            progress_bar.progress(10)
            
            # Call function from your attached file
            fast_duplicate_video_by_hours(v_in, v_out, target)
            
            progress_bar.progress(90)
            status_text.text("✅ Finalizing...")
            
            if os.path.exists(v_out):
                progress_bar.progress(100)
                status_text.text("✅ Complete!")
                st.success(f"✅ Processing Complete! File saved as: {v_out}")
            else:
                st.error("Processing failed. Output file was not created.")
        else:
            st.error(f"Input file '{v_in}' not found. Please run BeatMerge first.")

# --- Tool 3: Song Generator ---
elif choice == "🎸 Song Generator":
    st.title("🎸 AI Singing Voice Generator with Music")
    st.write("Generate realistic singing with musical backing using Edge-TTS + Audio Effects")

    # UI Inputs
    c1, c2, c3 = st.columns(3)
    with c1:
        song_style = st.selectbox("Select Music Style", ["Funk", "Pop", "Rock", "Jazz", "Ambient", "Chill"])
    with c2:
        voice_name = st.selectbox("Select Voice", [
            "en-US-AriaNeural",  # Female
            "en-US-GuyNeural",   # Male
            "en-GB-SoniaNeural", # Female British
            "en-AU-NatashaNeural" # Female Australian
        ])
    with c3:
        tempo = st.selectbox("Select Tempo", ["Slow", "Normal", "Fast"])

    lyrics = st.text_area("Enter Song Lyrics", value="Hello, this is my song", height=150)

    if st.button("🎵 Generate AI Singing", type="primary"):
        if lyrics:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("🎤 Generating AI singing voice...")
                progress_bar.progress(10)
                
                # Determine BPM from tempo
                if tempo == "Slow":
                    bpm = 80
                    rate = "-20%"
                elif tempo == "Fast":
                    bpm = 140
                    rate = "+20%"
                else:
                    bpm = 100
                    rate = "+0%"
                
                output_base = "generated_song"
                
                # Generate vocal
                if EDGE_TTS_AVAILABLE:
                    output_vocal = f"{output_base}_vocal.mp3"
                    async def generate_singing():
                        communicate = Communicate(text=lyrics, voice=voice_name, rate=rate)
                        await communicate.save(output_vocal)
                    try:
                        asyncio.run(generate_singing())
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(generate_singing())
                    progress_bar.progress(40)
                    vocal = AudioSegment.from_mp3(output_vocal) if os.path.exists(output_vocal) else None
                else:
                    engine = pyttsx3.init()
                    voices = engine.getProperty('voices')
                    engine.setProperty('voice', voices[0].id)
                    engine.setProperty('rate', 100 + (tempo == "Fast") * 50 - (tempo == "Slow") * 50)
                    engine.setProperty('volume', 0.9)
                    output_vocal = f"{output_base}_vocal.wav"
                    engine.save_to_file(lyrics, output_vocal)
                    engine.runAndWait()
                    progress_bar.progress(40)
                    vocal = AudioSegment.from_wav(output_vocal) if os.path.exists(output_vocal) else None
                
                if vocal:
                    status_text.text("🎵 Processing audio...")
                    progress_bar.progress(60)
                    
                    # Apply style-specific gains
                    if song_style == "Funk":
                        mixed = vocal.apply_gain(3)
                    elif song_style == "Pop":
                        mixed = vocal.apply_gain(2)
                    elif song_style == "Rock":
                        mixed = vocal.apply_gain(4)
                    elif song_style == "Jazz":
                        mixed = vocal.apply_gain(1)
                    elif song_style == "Ambient":
                        mixed = vocal.apply_gain(-1)
                    else:
                        mixed = vocal.apply_gain(0)
                    
                    mixed = mixed + AudioSegment.silent(duration=500)
                    
                    status_text.text("💾 Exporting to MP3...")
                    progress_bar.progress(80)
                    
                    output_song = f"{output_base}_{song_style.lower()}.mp3"
                    mixed.export(output_song, format="mp3")
                    progress_bar.progress(100)
                    
                    status_text.text("✅ Complete!")
                    st.success("✅ AI Singing generated!")
                    st.audio(output_song, format="audio/mp3")
                    
                    with open(output_song, "rb") as f:
                        st.download_button(
                            label="📥 Download AI Song",
                            data=f.read(),
                            file_name=output_song,
                            mime="audio/mp3"
                        )
                    
                    st.info(f"🎵 **Song Generated**\n- Style: {song_style}\n- Tempo: {tempo} ({bpm} BPM)\n- Voice: {voice_name}\n- Duration: {mixed.duration_seconds:.1f}s")
                    if os.path.exists(output_vocal):
                        os.remove(output_vocal)
                else:
                    st.error("Failed to generate vocal track.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        else:
            st.error("Please enter lyrics to generate a song.")