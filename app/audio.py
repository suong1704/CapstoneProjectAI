from pydub import AudioSegment

# save to database
class AudioUtil:
    def get_media_duration(file):
        audio = AudioSegment.from_file(file)
        return round(len(audio) / 1000, 2)