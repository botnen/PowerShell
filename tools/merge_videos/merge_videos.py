import os
import glob
from datetime import datetime

import click
from moviepy.editor import VideoFileClip, concatenate_videoclips


def extract_timestamp(filename):
    basename = os.path.basename(filename)
    timestamp_str = basename.split('_')[0]
    return datetime.strptime(timestamp_str, "%Y%m%dT%H%M")


def is_session_ready(folder):
    ts_files = glob.glob(os.path.join(folder, '*.ts'))
    mp4_files = glob.glob(os.path.join(folder, '**', '*.mp4'), recursive=True)
    return len(ts_files) == 0 and len(mp4_files) > 0


def discover_video_files(folders):
    video_files = []
    for folder in folders:
        if is_session_ready(folder):
            mp4_files = glob.glob(os.path.join(folder, '**', '*.mp4'), recursive=True)
            video_files.extend(mp4_files)
        else:
            click.echo(f"Skipping folder (not ready): {folder}")
    return video_files


def group_into_sessions(video_files, timestamp_threshold_minutes=30, time_threshold_hours=1):
    if not video_files:
        return []

    sorted_files = sorted(video_files, key=extract_timestamp)
    sessions = [[sorted_files[0]]]

    for f in sorted_files[1:]:
        prev = sessions[-1][-1]
        timestamp_diff = (extract_timestamp(f) - extract_timestamp(prev)).total_seconds() / 60
        time_diff = (os.path.getmtime(f) - os.path.getmtime(prev)) / 3600

        if timestamp_diff <= timestamp_threshold_minutes and time_diff <= time_threshold_hours:
            sessions[-1].append(f)
        else:
            sessions.append([f])

    return sessions


def merge_video_group(video_files, output_path):
    video_files = sorted(video_files, key=extract_timestamp)
    clips = [VideoFileClip(f) for f in video_files]
    try:
        merged_clip = concatenate_videoclips(clips)
        merged_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
    finally:
        for clip in clips:
            clip.close()


@click.command()
@click.option('--folders', multiple=True, required=True, help='Folders to scan for video files.')
@click.option('--output-dir', required=True, help='Directory to write merged videos to.')
@click.option('--timestamp-threshold', default=30, help='Max minutes between timestamps to group files.')
@click.option('--time-threshold', default=1, help='Max hours between modification times to group files.')
def main(folders, output_dir, timestamp_threshold, time_threshold):
    for folder in folders:
        if not os.path.isdir(folder):
            click.echo(f"Warning: folder does not exist: {folder}", err=True)

    os.makedirs(output_dir, exist_ok=True)

    video_files = discover_video_files(folders)
    sessions = group_into_sessions(video_files, timestamp_threshold, time_threshold)

    for i, session in enumerate(sessions):
        output_name = f"merged_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{i}.mp4"
        output_path = os.path.join(output_dir, output_name)
        click.echo(f"Merging session {i} ({len(session)} files) -> {output_path}")
        merge_video_group(session, output_path)


if __name__ == '__main__':
    main()
