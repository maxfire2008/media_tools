import subprocess
import os
import argparse

# Define the path to your FFmpeg executable
ffmpeg_path = "C:\\bin\\ffmpeg.exe"
ffprobe_path = "C:\\bin\\ffprobe.exe"


def get_video_duration(video_path):
    ffprobe_args = (
        "-v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1"
    )

    cmd = f'{ffprobe_path} {ffprobe_args} "{video_path}"'
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)

    if output:
        duration = float(output)
        return duration
    return None


def get_new_resolution(width, height, max_width, max_height):
    aspect_width = max_height * width / height
    aspect_height = max_width * height / width

    if aspect_width >= max_width:
        return max_width, int(round(aspect_height))
    else:
        return int(round(aspect_width)), max_height


def get_video_info(input_path):
    ffprobe_args = "-v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -of default=noprint_wrappers=1:nokey=1"

    cmd = f'{ffprobe_path} {ffprobe_args} "{input_path}"'
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)

    video_info = output.split()
    if len(video_info) == 3:
        width, height = map(int, video_info[:2])
        numerator, denominator = map(int, video_info[2].split("/"))
        frame_rate = numerator / denominator
        return width, height, frame_rate
    return None


def get_tracks(input_path):
    # check for audio
    ffprobe_args = "-v error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1"
    cmd = f'{ffprobe_path} {ffprobe_args} "{input_path}"'
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    audio = output.split()
    # check for video
    ffprobe_args = "-v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1"
    cmd = f'{ffprobe_path} {ffprobe_args} "{input_path}"'
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    video = output.split()

    return bool(audio), bool(video)


def compress_video(input_path, output_path, target_bitrate):
    limits = [
        [10000000, 3840, 2160, 60, "h264_nvenc"],
        [5000000, 1920, 1080, 50, "h264_nvenc"],
        [2000000, 1280, 720, 25, "h264_nvenc"],
        [1000000, 854, 480, 15, "h264_nvenc"],
        [500000, 640, 360, 10, "h264_nvenc"],
        [0, 256, 144, 5, "h264_nvenc"],
    ]
    # min_bitrate, max_width, max_height, max_frame_rate

    audio_exists, video_exists = get_tracks(input_path)

    if audio_exists and video_exists:
        audio_bitrate = min(128000, target_bitrate / 8)
        audio_bitrate = max(500, audio_bitrate)
        video_bitrate = target_bitrate - audio_bitrate
        video_bitrate = max(500, video_bitrate)
    elif audio_exists:
        audio_bitrate = max(500, target_bitrate)
        video_bitrate = 0
    else:
        audio_bitrate = 0
        video_bitrate = max(500, target_bitrate)
    print(f"Target bitrate: {target_bitrate} bps")
    print(f"Target video bitrate: {video_bitrate} bps")
    print(f"Target audio bitrate: {audio_bitrate} bps")

    video_info = get_video_info(input_path)
    if video_exists:
        if not video_info:
            print("Failed to get video information. Compression aborted.")
            return
        width, height, frame_rate = video_info

        for limit in sorted(limits, reverse=True):
            min_bitrate, max_width, max_height, max_frame_rate, video_encoder = limit
            if video_bitrate >= min_bitrate:
                break

        new_width, new_height = get_new_resolution(width, height, max_width, max_height)
        new_width += new_width % 2
        new_height += new_height % 2
        new_frame_rate = min(frame_rate, max_frame_rate)

        vf_filter = f"scale={new_width}:{new_height}"

    cmd = [
        ffmpeg_path,
        "-i",
        input_path,
    ]
    if video_exists:
        cmd += [
            "-c:v",
            video_encoder,
            "-r",
            str(new_frame_rate),
            "-vf",
            vf_filter,
            "-b:v",
            f"{int(round(video_bitrate))}",
        ]
    if audio_exists:
        if audio_bitrate > 64000:
            audio_codec = "aac"
        else:
            audio_codec = "libopus"
        cmd += [
            "-c:a",
            audio_codec,
            "-b:a",
            f"{int(round(audio_bitrate))}",
        ]
    cmd += [
        output_path,
        "-y",
    ]
    subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        check=True,
    )


def get_file_length(length):
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    for unit in units:
        if length < 1024:
            break
        length /= 1024
    return "{:.2f} {}".format(length, unit)


def main():
    parser = argparse.ArgumentParser(description="Video compression tool using FFmpeg")
    parser.add_argument("input_path", help="Path to the input video file")
    parser.add_argument(
        "target_file_size",
        help="Target file size in MB for the compressed video",
    )
    args = parser.parse_args()

    video_path = args.input_path
    target_file_size = args.target_file_size

    if not os.path.exists(video_path):
        print("The provided video file doesn't exist.")
        return

    # Get video duration
    duration = get_video_duration(video_path)
    if not duration:
        print("Failed to get video duration.")
        return

    # Calculate the target bitrate based on the desired file size
    if target_file_size.endswith("K"):
        target_file_size = float(target_file_size[:-1]) * 1024
    else:
        target_file_size = float(target_file_size) * 1024 * 1024
    target_bitrate = (target_file_size * 8 / duration) * 0.95

    current_size = os.path.getsize(video_path)

    # Compress the video and save it to a new file
    temp_video_path = video_path
    tries = 0
    last_size = current_size

    file_extension = ".mp4"

    while current_size >= target_file_size:
        if tries >= 1:
            target_bitrate *= (target_file_size / current_size) * 0.95
        temp_video_path = os.path.splitext(video_path)[0] + "_temp" + file_extension

        compress_video(video_path, temp_video_path, target_bitrate)

        last_size = current_size
        current_size = os.path.getsize(temp_video_path)
        tries += 1
        if tries >= 5 or last_size == current_size:
            print("Failed to compress the video to required size.")
            break

    current_size = os.path.getsize(temp_video_path)
    new_video_path = (
        os.path.splitext(video_path)[0]
        + "_"
        + str(round(current_size / (1024**2), 2))
        + "MiB"
        + file_extension
    )

    # copy the last temp video to the new video path
    i = 0
    while True:
        try:
            new_video_path = (
                os.path.splitext(video_path)[0]
                + "_"
                + str(round(current_size / (1024**2), 2))
                + "MiB"
            )
            if i != 0:
                new_video_path += "_" + str(i)
            new_video_path += file_extension
            os.rename(temp_video_path, new_video_path)
            break
        except FileExistsError:
            i += 1

    # Check the new file size and notify the user
    new_file_size = os.path.getsize(new_video_path)
    print("Compression complete!")
    print(f"Original video duration: {duration} seconds")
    print(f"Target file size: {round(target_file_size/(1024**2),3)} MiB")
    print(f"Compressed file size: {get_file_length(new_file_size)}")
    print(f"New video saved to: {new_video_path}")


if __name__ == "__main__":
    main()
