# FFmpeg Video Converter with GPU

This is a GUI application for converting MKV video files to MP4 format using FFmpeg. The application detects your GPU (NVIDIA or AMD) and uses the appropriate hardware-accelerated encoder to speed up the conversion process.

## Features

- Add multiple MKV files to a queue for batch conversion.
- Select the output directory for the converted files.
- Browse and select the FFmpeg executable.
- Detect the GPU and use hardware acceleration for conversion.
- Track conversion progress with a progress bar and percentage indicator.
- Display logs of the conversion process.
- Display the number of videos left in the queue.
- Remembering the paths for ffmpeg and output path. (Keeping them in config)

## Prerequisites

- Python 3.x
- FFmpeg 
- `GPUtil` library (install with `pip install gputil`)
- `setuptools` library (install with `pip install setuptools`)

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/eslorex/ffmpeg-video-converter.git
   cd ffmpeg-video-converter
   ```

2. Install the required Python packages:
   ```sh
   pip install -r requirements.txt
   ```

3. Ensure FFmpeg is installed and accessible. You can download FFmpeg from [here](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z).

## Usage

1. Use the "Add to Queue" button to add MKV files to the queue.

2. Use the "Remove from Queue" button to remove selected files from the queue.

3. Click on "Browse..." next to "Select Output Directory" to choose where the converted files will be saved.

4. Click on "Browse..." next to "Select FFmpeg Executable" to select the FFmpeg executable file.

5. The application will detect your GPU and display the information.

6. Click on "Start Conversion" to begin converting the files in the queue. The progress bar and logs will update to show the conversion status.

7. The label "Videos in Queue" will update to show the number of videos left in the queue.

## Troubleshooting

- Ensure FFmpeg is properly installed and the path to the executable is correctly set.
- Make sure the required Python packages are installed.

## License

This project is licensed under the MIT License.
