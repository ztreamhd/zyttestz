#!/usr/bin/env python3
"""
YouTube Livestream M3U8 Extractor
Extracts HLS master playlist URLs from YouTube live streams.
"""

import os
import re
import json
from pathlib import Path
import yt_dlp

PLAYLISTS_DIR = Path("playlists")
PLAYLISTS_DIR.mkdir(exempt_ok=True)

def sanitize_filename(name: str) -> str:
    """Sanitize channel/stream name for filename."""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name).strip('-').lower()
    return name or "unknown"

def get_live_stream_url(channel_input: str):
    """Extract M3U8 URL for a YouTube live stream."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
        'format': 'best',
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'ios'],
            }
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Handle channel handles / IDs by constructing live URL
            if channel_input.startswith('@') or channel_input.startswith('UC'):
                if channel_input.startswith('@'):
                    url = f"https://www.youtube.com/{channel_input}/live"
                else:
                    url = f"https://www.youtube.com/channel/{channel_input}/live"
            else:
                url = channel_input

            info = ydl.extract_info(url, download=False)

            # Check if it's actually live
            if not info.get('is_live', False):
                print(f"⚠️  {channel_input} is not currently live")
                return None, None

            title = info.get('title', 'Unknown Stream')
            channel = info.get('uploader', info.get('channel', 'Unknown'))

            # Prefer explicit manifest_url or find HLS format
            formats = info.get('formats', [])
            hls_url = None

            # Try to find best HLS manifest
            for fmt in sorted(formats, key=lambda x: x.get('height', 0) or 0, reverse=True):
                if fmt.get('protocol') in ('m3u8', 'm3u8_native') or \
                   (fmt.get('url', '').endswith('.m3u8') or 'manifest' in fmt.get('url', '')):
                    hls_url = fmt['url']
                    break

            # Fallback to direct url if it's HLS
            if not hls_url and info.get('url', '').endswith('.m3u8'):
                hls_url = info['url']

            if not hls_url:
                print(f"⚠️  Could not find HLS URL for {channel_input}")
                return None, None

            return hls_url, {
                'title': title,
                'channel': channel,
                'original_input': channel_input
            }

    except Exception as e:
        print(f"❌ Error processing {channel_input}: {e}")
        return None, None

def create_m3u8_file(stream_info: dict, hls_url: str, filename: str):
    """Create a single stream M3U8 playlist file."""
    content = f"""#EXTM3U
#EXTINF:-1 tvg-id="{stream_info['channel']}" tvg-name="{stream_info['title']}" group-title="YouTube Live",{stream_info['channel']}
{hls_url}
"""
    filepath = PLAYLISTS_DIR / f"{filename}.m3u8"
    filepath.write_text(content, encoding='utf-8')
    print(f"✅ Created {filepath.name}")

def create_combined_m3u(streams: list):
    """Create combined M3U playlist."""
    lines = ["#EXTM3U"]

    for stream in streams:
        lines.append(
            f'#EXTINF:-1 tvg-id="{stream["channel"]}" tvg-name="{stream["title"]}" '
            f'group-title="YouTube Live",{stream["channel"]}\n{stream["url"]}'
        )

    content = "\n".join(lines)
    filepath = PLAYLISTS_DIR / "all_streams.m3u"
    filepath.write_text(content, encoding='utf-8')
    print(f"✅ Created combined playlist: {filepath.name} ({len(streams)} streams)")

def main():
    channels_file = Path("channels.txt")
    if not channels_file.exists():
        print("channels.txt not found!")
        return

    channels = [line.strip() for line in channels_file.read_text().splitlines() if line.strip() and not line.startswith('#')]

    print(f"🔍 Processing {len(channels)} entries...\n")

    successful_streams = []

    for channel in channels:
        print(f"Processing: {channel}")
        hls_url, meta = get_live_stream_url(channel)

        if hls_url and meta:
            filename = sanitize_filename(meta['channel'])
            create_m3u8_file(meta, hls_url, filename)

            successful_streams.append({
                'url': hls_url,
                'title': meta['title'],
                'channel': meta['channel']
            })
        print()

    if successful_streams:
        create_combined_m3u(successful_streams)
        print(f"\n🎉 Done! {len(successful_streams)} live streams extracted.")
    else:
        print("\nNo live streams found at this time.")

if __name__ == "__main__":
    main()
