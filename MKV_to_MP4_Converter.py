import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import json
import threading
import GPUtil
import re
from subprocess import CREATE_NO_WINDOW

config_file = 'config.json'

def load_config():
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(config_file, 'w') as f:
        json.dump(config, f)

def update_queue_count():
    queue_count_label.config(text=f"Videos in Queue: {queue_listbox.size()}")

def add_to_queue():
    file_paths = filedialog.askopenfilenames(filetypes=[("MKV files", "*.mkv")], initialdir=config.get('last_input_dir', default_dir))
    if file_paths:
        for file_path in file_paths:
            queue_listbox.insert(tk.END, file_path)
        config['last_input_dir'] = os.path.dirname(file_paths[0])
        save_config(config)
    update_queue_count()

def remove_from_queue():
    selected_indices = queue_listbox.curselection()
    for index in selected_indices[::-1]:
        queue_listbox.delete(index)
    update_queue_count()

def select_output_directory():
    directory_path = filedialog.askdirectory(initialdir=config.get('last_output_dir', default_dir))
    if directory_path:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, directory_path)
        config['last_output_dir'] = directory_path
        save_config(config)

def select_ffmpeg_executable():
    file_path = filedialog.askopenfilename(filetypes=[("Executable files", "*.exe")], initialdir=config.get('last_ffmpeg_dir', default_dir))
    if file_path:
        ffmpeg_entry.delete(0, tk.END)
        ffmpeg_entry.insert(0, file_path)
        config['last_ffmpeg_path'] = file_path
        config['last_ffmpeg_dir'] = os.path.dirname(file_path)
        save_config(config)
        detect_gpu()

def detect_gpu():
    gpus = GPUtil.getGPUs()
    main_gpu = None
    gpu_type = "None"
    gpu_info = "None"

    if gpus:
        main_gpu = max(gpus, key=lambda gpu: gpu.memoryTotal)
        if 'NVIDIA' in main_gpu.name:
            gpu_type = "NVIDIA"
        elif 'AMD' in main_gpu.name or 'Radeon' in main_gpu.name:
            gpu_type = "AMD"
        else:
            gpu_type = "Unknown"
        gpu_info = main_gpu.name
    else:
        try:
            result = subprocess.run(["wmic", "path", "win32_videocontroller", "get", "description"], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            gpu_lines = result.stdout.strip().split("\n")[1:]
            for line in gpu_lines:
                if "AMD" in line or "Radeon" in line:
                    main_gpu = line.strip()
                    break
            if main_gpu:
                gpu_type = "AMD"
                gpu_info = main_gpu.replace("AMD ", "").replace("Radeon ", "").strip()
            else:
                gpu_info = "None"
        except Exception as e:
            gpu_info = "None"

    gpu_label_var.set(f"Detected GPU: {gpu_type} - {gpu_info}")
    config['last_gpu_type'] = gpu_type
    save_config(config)

def get_supported_streams(ffmpeg_path, input_file):
    try:
        result = subprocess.run([ffmpeg_path, '-hide_banner', '-i', input_file], stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW)
        streams = []
        for line in result.stderr.split('\n'):
            if 'Stream #' in line:
                streams.append(line)
        video_streams = [s for s in streams if 'Video' in s]
        audio_streams = [s for s in streams if 'Audio' in s]
        return video_streams, audio_streams
    except Exception as e:
        print(f"Error probing streams: {e}")
        return [], []

def update_progress_bar(line, progress_var, text_widget, percentage_label, duration):
    text_widget.insert(tk.END, line + "\n")
    text_widget.see(tk.END)

    time_pattern = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')

    match_time = time_pattern.search(line)
    if match_time and duration:
        h, m, s = map(float, match_time.groups())
        current_time = h * 3600 + m * 60 + s
        percentage = (current_time / duration) * 100
        progress_var.set(percentage)
        percentage_label.config(text=f"{percentage:.2f}%")
        app.update_idletasks()  # Ensure the UI updates

def run_ffmpeg(command, progress_var, text_widget, percentage_label, status_label, callback, duration):
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=CREATE_NO_WINDOW)
        while True:
            line = process.stdout.readline()
            if line == '' and process.poll() is not None:
                break
            if line:
                update_progress_bar(line.strip(), progress_var, text_widget, percentage_label, duration)
        rc = process.poll()
        if rc != 0:
            raise subprocess.CalledProcessError(rc, command)
        progress_var.set(100)
        percentage_label.config(text="100%")
        status_label.config(text="Video conversion completed successfully!")
    except subprocess.CalledProcessError as e:
        error_message = f"Video conversion failed:\n\nCommand:\n{e.cmd}\n\nError:\n{e.output}"
        with open("ffmpeg_error_log.txt", "w") as log_file:
            log_file.write(error_message)
        messagebox.showerror("Error", error_message)
    finally:
        callback()

def get_video_duration(ffmpeg_path, input_file):
    try:
        result = subprocess.run([ffmpeg_path, '-i', input_file], stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW)
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        if duration_match:
            hours, minutes, seconds = map(float, duration_match.groups())
            return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        print(f"Error getting duration: {e}")
    return None

def convert_next_in_queue():
    if queue_listbox.size() > 0:
        input_file = queue_listbox.get(0)
        output_dir = output_entry.get()
        ffmpeg_path = ffmpeg_entry.get()
        gpu_type = gpu_label_var.get().split(": ")[1].split(" - ")[0]
        
        if not input_file or not output_dir or not ffmpeg_path:
            messagebox.showerror("Error", "Please select input file, output directory, and FFmpeg executable.")
            return
        
        output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(input_file))[0] + "_converted.mp4")
        
        if gpu_type == "NVIDIA":
            encoder = "h264_nvenc"
            options = "-pix_fmt yuv420p"
        elif gpu_type == "AMD":
            encoder = "h264_amf"
            options = ""
        else:
            messagebox.showerror("Error", "Unsupported GPU type detected.")
            return
        
        video_streams, audio_streams = get_supported_streams(ffmpeg_path, input_file)
        if not video_streams and not audio_streams:
            messagebox.showerror("Error", "No supported video or audio streams found.")
            return
        
        stream_map = ' '.join([f'-map 0:v:{i}' for i in range(len(video_streams))]) + ' ' + ' '.join([f'-map 0:a:{i}' for i in range(len(audio_streams))])
        
        command = f'"{ffmpeg_path}" -y -i "{input_file}" {stream_map} -c:v {encoder} {options} -preset fast "{output_file}"'
        
        duration = get_video_duration(ffmpeg_path, input_file)
        if duration is None:
            messagebox.showerror("Error", "Could not get video duration.")
            return
        
        progress_var.set(0)
        threading.Thread(target=run_ffmpeg, args=(command, progress_var, text_widget, percentage_label, status_label, on_conversion_complete, duration)).start()

def on_conversion_complete():
    queue_listbox.delete(0)
    update_queue_count()
    if queue_listbox.size() > 0:
        convert_next_in_queue()

def start_conversion():
    if queue_listbox.size() > 0:
        convert_next_in_queue()
    else:
        messagebox.showinfo("Info", "No videos in the queue to convert.")

config = load_config()
default_dir = os.path.dirname(os.path.abspath(__file__))

app = tk.Tk()
app.title("FFmpeg Video Converter with GPU")

style = ttk.Style()
style.configure("TLabel", font=("Helvetica", 12))
style.configure("TButton", font=("Helvetica", 12))
style.configure("TEntry", font=("Helvetica", 12))
style.configure("TProgressbar", thickness=20)

tk.Label(app, text="Queue:", font=("Helvetica", 14)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
queue_listbox = tk.Listbox(app, height=10, width=50, selectmode=tk.MULTIPLE, font=("Helvetica", 12))
queue_listbox.grid(row=1, column=0, columnspan=3, padx=10, pady=5)
queue_scrollbar = tk.Scrollbar(app, orient=tk.VERTICAL, command=queue_listbox.yview)
queue_scrollbar.grid(row=1, column=3, sticky="ns")
queue_listbox.config(yscrollcommand=queue_scrollbar.set)

button_frame = tk.Frame(app)
button_frame.grid(row=2, column=0, columnspan=3, pady=5)

tk.Button(button_frame, text="Add to Queue", command=add_to_queue, font=("Helvetica", 12)).grid(row=0, column=0, padx=5)
tk.Button(button_frame, text="Remove from Queue", command=remove_from_queue, font=("Helvetica", 12)).grid(row=0, column=1, padx=5)

queue_count_label = tk.Label(app, text="Videos in Queue: 0", font=("Helvetica", 12))
queue_count_label.grid(row=2, column=2, padx=10, pady=5, sticky="e")

tk.Label(app, text="Select Output Directory:", font=("Helvetica", 12)).grid(row=3, column=0, padx=10, pady=5, sticky="e")
output_entry = tk.Entry(app, width=50, font=("Helvetica", 12))
output_entry.grid(row=3, column=1, padx=10, pady=5)
tk.Button(app, text="Browse...", command=select_output_directory, font=("Helvetica", 12)).grid(row=3, column=2, padx=10, pady=5)

tk.Label(app, text="Select FFmpeg Executable:", font=("Helvetica", 12)).grid(row=4, column=0, padx=10, pady=5, sticky="e")
ffmpeg_entry = tk.Entry(app, width=50, font=("Helvetica", 12))
ffmpeg_entry.grid(row=4, column=1, padx=10, pady=5)
tk.Button(app, text="Browse...", command=select_ffmpeg_executable, font=("Helvetica", 12)).grid(row=4, column=2, padx=10, pady=5)

gpu_label_var = tk.StringVar(value="Detected GPU: None")
tk.Label(app, textvariable=gpu_label_var, font=("Helvetica", 12, "bold")).grid(row=5, column=0, columnspan=3, padx=10, pady=5)

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(app, variable=progress_var, maximum=100, style="TProgressbar")
progress_bar.grid(row=6, column=0, columnspan=3, padx=10, pady=5, sticky="we")

percentage_label = tk.Label(app, text="0%", font=("Helvetica", 12))
percentage_label.grid(row=7, column=0, columnspan=3, pady=5)

text_widget = tk.Text(app, height=10, font=("Helvetica", 12))
text_widget.grid(row=8, column=0, columnspan=3, padx=10, pady=5, sticky="we")

status_label = tk.Label(app, text="", font=("Helvetica", 12, "italic"))
status_label.grid(row=9, column=0, columnspan=3, pady=5)

tk.Button(app, text="Start Conversion", command=start_conversion, font=("Helvetica", 12)).grid(row=10, column=0, columnspan=3, pady=10)

output_entry.insert(0, config.get('last_output_dir', ''))
ffmpeg_entry.insert(0, config.get('last_ffmpeg_path', ''))

detect_gpu()

update_queue_count()

app.mainloop()
