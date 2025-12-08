#!/usr/bin/env python3
"""
Transcribe audio file using OpenAI Whisper
"""
import whisper
import sys
import os

def transcribe_audio(audio_file_path, output_file=None):
    """
    Transcribe an audio file using Whisper
    
    Args:
        audio_file_path: Path to the audio file
        output_file: Optional path to save transcription (default: audio_file_name.txt)
    """
    if not os.path.exists(audio_file_path):
        print(f"Error: File '{audio_file_path}' not found.")
        sys.exit(1)
    
    print(f"Loading Whisper model...")
    # Using 'base' model - good balance of speed and accuracy
    # Options: tiny, base, small, medium, large
    model = whisper.load_model("base")
    
    print(f"Transcribing '{audio_file_path}'...")
    result = model.transcribe(audio_file_path)
    
    transcription = result["text"]
    
    # Determine output file path
    if output_file is None:
        base_name = os.path.splitext(audio_file_path)[0]
        output_file = f"{base_name}_transcription.txt"
    
    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(transcription)
    
    print(f"\nTranscription complete!")
    print(f"Saved to: {output_file}")
    print(f"\nTranscription preview:\n{transcription[:500]}...")
    
    return transcription

if __name__ == "__main__":
    audio_file = "output.wav"
    
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    
    transcribe_audio(audio_file)




