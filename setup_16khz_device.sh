#!/bin/bash
# Setup a 16kHz virtual device for better Whisper transcription

echo "Setting up 16kHz virtual audio device for Claude Voice..."

# Create a null sink at 16kHz
pactl load-module module-null-sink \
    sink_name=claude_voice_16k \
    rate=16000 \
    sink_properties="device.description='Claude Voice 16kHz'"

# Create a loopback from Arctis to the 16kHz sink
pactl load-module module-loopback \
    source="alsa_input.usb-SteelSeries_Arctis_Nova_Pro_Wireless-00.mono-fallback" \
    sink=claude_voice_16k \
    rate=16000 \
    latency_msec=1

# Create a virtual source from the sink's monitor
SOURCE_NAME=$(pactl list sources short | grep claude_voice_16k.monitor | awk '{print $2}')

echo "Virtual 16kHz device created!"
echo "To use it, set this as your default input:"
echo "  pactl set-default-source $SOURCE_NAME"
echo ""
echo "Or select 'Claude Voice 16kHz' in your audio settings"