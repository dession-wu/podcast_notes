"""One bounded local transcription process, invoked only by mini worker."""
import json
import os
import sys
from pathlib import Path
from core.smart_transcriber import SmartTranscriber
from models.podcast import PodcastEpisode

if __name__ == '__main__':
    episode = PodcastEpisode(**json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    output = Path(sys.argv[2])
    mode = os.getenv('MINI_TRANSCRIPT_MODE', 'basic')
    if mode == 'dialogue':
        from backend.mini.dialogue import transcribe_dialogue
        result = transcribe_dialogue(episode.local_audio_path)
        output.write_text(result['text'], encoding='utf-8')
        output.with_suffix('.segments.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    elif mode == 'basic':
        result = SmartTranscriber().transcribe(episode)
        output.write_text(result.to_txt() if result.segments else result.text, encoding='utf-8')
    else:
        raise ValueError('MINI_TRANSCRIPT_MODE must be basic or dialogue')
