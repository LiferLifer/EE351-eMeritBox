import vlc
import time, os

class BGMPlayer:
    def __init__(self):
        self.instance = vlc.Instance('--no-xlib')
        self.player = self.instance.media_player_new()

    def load_music(self, music_path):
        media = self.instance.media_new(music_path)
        self.player.set_media(media)

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

if __name__ == "__main__":
    player = BGMPlayer()
    music_path = "../res/ysf.mp3"
    player.load_music(music_path)

    player.play()
    time.sleep(5)

    player.pause()
    time.sleep(2)

    player.play()
    time.sleep(5)
        
    player.stop()
