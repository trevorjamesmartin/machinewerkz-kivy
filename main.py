from os import getcwd, path, listdir
from time import time, sleep
from random import randint, shuffle
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics.vertex_instructions import Rectangle
from kivy.config import Config
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty
from kivy.utils import platform
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.logger import Logger
from kivy.uix.settings import SettingsWithSpinner
from kivy.core.window import Window
from audio import fx_dict, music_list

from audio import load_audio
from game import PuzzlePiece, GameBoard, LEFT, RIGHT, screen_grid, get_square_unit

try:
    Logger.info('[MachineWerkz] setting defaults')
    MW_DEFAULT = {
        'fx_folder': path.join(getcwd(), 'data/audio/fx'),
        'music_folder': path.join(getcwd(), 'data/audio/music'),
        'cols': "10",
        'rows': "18",
        'square_unit': "50"
    }
except Exception as e:
    raise e
SU = int(MW_DEFAULT['square_unit'])
ROWS = int(MW_DEFAULT['rows'])
COLS = int(MW_DEFAULT['cols'])

INI = path.join(getcwd(), 'machinewerkz.ini')

if path.isfile(INI):
    Config.read(INI)
    Logger.info('[MachineWerkz] loading configuration')
    PLAYLIST = music_list(Config.get('machinewerkz', 'music_folder'))
    FX = fx_dict(Config.get('machinewerkz', 'fx_folder'))
    ROWS = int(Config.get('machinewerkz', 'rows'))
    COLS = int(Config.get('machinewerkz', 'cols'))
else:
    PLAYLIST = music_list(MW_DEFAULT['music_folder'])
    FX = fx_dict(MW_DEFAULT['fx_folder'])
    ROWS = int(MW_DEFAULT['rows'])
    COLS = int(MW_DEFAULT['cols'])


if not platform in ['linux', 'window', 'mac']:
    SU = Window.size[0] / float(COLS)

SCREEN_WIDTH = SU * COLS
SCREEN_HEIGHT = SU * ROWS

Window.size = (SCREEN_WIDTH, SCREEN_HEIGHT)

SU = Window.size[0] / float(COLS)

print(SU)

Config.window_icon = path.join(getcwd(), 'data/img/steampunk.png')


Config.set('kivy', 'exit_on_escape', '0')

__version__ = "0.5.1"


Config.set('graphics', 'resizable', '0')


class FileBox(BoxLayout):
    pass


class FileBrowserScreen(Screen):
    pass


class SettingsScreen(Screen):
    pass


class MenuScreen(Screen):
    pass


class GameScreen(Screen):
    pass


class SettingsMenu(BoxLayout):
    pass


class MainMenu(BoxLayout):
    pass


class BoundingBox(BoxLayout):
    pass


class PuzzleGameWidget(Widget):
    tock = 0
    last_state = None
    event = None
    LIT_IMG = StringProperty("data/img/steampunk.png")
    DARK_IMG = StringProperty("data/img/empty.png")
    texture = Image(source="data/img/steampunk.png").texture
    piece_group = None
    last_t = 0
    test_event = None

    def __init__(self, **kwargs):
        super(PuzzleGameWidget, self).__init__(**kwargs)
        app = App.get_running_app()
        self.piece = app.piece
        self.board = app.game_board
        self.piece_group = InstructionGroup()
        self.canvas.add(self.piece_group)
        Clock.schedule_interval(self.next_state, .1)

    def on_touch_down(self, touch):
        app = App.get_running_app()
        su = get_square_unit(COLS, Window.size[0])
        _x, _y = touch.pos
        x, y = _x/su, _y/su
        app.modify_state([int(x), int(y)])

    @mainthread
    def draw_method(self, grid):
        # update InstructionGroup() for widget canvas
        self.piece_group.clear()
        for y in range(len(grid)):
            for x in range(len(grid[0])):
                lit = [False, True][int(grid[y][x])]
                if lit:
                    rx = x * self.board.square_unit
                    ry = Window.height - (y+1) * self.board.square_unit
                    self.piece_group.add(
                        Rectangle(texture=self.texture, pos=(rx, ry),
                                  size=[self.board.square_unit, self.board.square_unit])
                    )
        return grid

    @mainthread
    def next_state(self, dt):
        app = App.get_running_app()
        f_speed = app.fall_speed
        ok, msg = self.piece.cb_draw(cb=self.draw_method, acb=app.audio_callback)
        if not ok:
            self.piece.swap_grid()
            self.piece.shape_shift()
            self.piece.reset()
            app.current_score = self.piece.text_score[0]
            # check if
            return True
        elapsed = time() - self.last_t
        if elapsed >= f_speed and self.piece.game_on:
            self.piece.fall()
            self.last_t = time()


class GameBoardLayout(BoxLayout):
    cols = COLS
    rows = ROWS
    screen_su = None

    def __init__(self, **kwargs):
        super(GameBoardLayout, self).__init__(**kwargs)
        app = App.get_running_app()
        game_board = GameBoard(cols=COLS, rows=ROWS, square_unit=SU)
        app.game_board = game_board
        self.screen_su = get_square_unit(self.cols, Window.size[0])
        app.widget_grid = screen_grid(self.rows, self.cols, Window.size)
        piece = PuzzlePiece(square_unit=SU, shape=randint(0, 6), state=True,
                       board=app.game_board, restart_callback=app.widget_reset)
        app.piece = piece
        app.game_engine = PuzzleGameWidget()


class MachineWerkz(App):
    lit = list()
    game_board, piece, game_engine = None, None, None
    widget_grid = None
    fall_speed = .9
    current_score = StringProperty('machine werkz')
    current_song = None
    music_state = True
    music_location = 'default'
    music_playlist = []
    music_played = []
    fx_bucket = []
    event = None
    spinner = None
    __manager = None
    __knock = 0

    def build(self, **kwargs):
        self.settings_cls = SettingsWithSpinner
        self.bind(on_start=self.init_device)
        self.music_playlist = [str(_) for _ in PLAYLIST]
        self.__manager = ScreenManager()
        self.__manager.add_widget(MenuScreen(name='menu'))
        self.__manager.add_widget(GameScreen(name='game'))
        self.__manager.add_widget(SettingsScreen(name='settings'))
        self.__manager.add_widget(FileBrowserScreen(name='file_box'))
        shuffle(PLAYLIST)
        self.play_music()
        return self.__manager

    def build_config(self, config):
        config.setdefaults('machinewerkz', {
            'fx_folder': path.join(getcwd(), 'data/audio/fx'),
            'music_folder': path.join(getcwd(), 'data/audio/music'),
            'cols': '10',
            'rows': '18',
            'square_unit': '50',
            'fall_speed': '1.618'
        })

    def build_settings(self, settings):
        settings.add_json_panel('machinewerkz', self.config, path.join(getcwd(), 'machinewerkz.json'))

    def on_config_change(self, config, section, key, value):
        if key == 'fall_speed':
            self.fall_speed = float(value)
        config.set(section, key, value)
        config.write()

    def init_device(self, *args):
        self.piece.pause()
        Window.bind(on_keyboard=self.on_kb)

    def on_kb(self, window, key1, key2, txt, modifiers):
        if key1 == 27 or key1 == 1001:
            self.__knock += 1
            if self.__knock > 2:
                return self.stop()
            return self.change_screen('menu')

    def empty_fx_bucket(self):
        for _ in range(len(self.fx_bucket)):
            _ = self.fx_bucket.pop(0)
            _.stop()
            del _

    def audio_callback(self, audio_type, audio_name, extra=None):
        if len(self.fx_bucket) > 10:
            self.empty_fx_bucket()
        if audio_type in ['fx', 'FX']:
            try:
                _ = load_audio(FX[audio_name])
                _.play()
                self.fx_bucket.append(_)
            except KeyError:
                pass

    def toggle_music(self):
        self.music_state = not self.music_state
        self.play_music()

    def play_music(self):
        if not self.music_state:
            try:
                self.current_song.stop()
            except TypeError:
                pass
            except AttributeError as e:
                if 'NoneType' in e:
                    pass
                raise e
            return "MUSIC OFF"
        # music for menus
        if self.__manager is not None and (self.__manager.current not in ['game']):
            try:
                s = FX['intro']
            except KeyError:
                return
        else:
            try:
                s = self.music_playlist.pop()
            except IndexError as e:
                self.music_playlist = [str(_) for _ in self.music_played]
                del self.music_played[:]
                s = self.music_playlist.pop()
        self.current_song = load_audio(s)
        self.music_played.append(str(s))
        self.current_song.play()

    def refresh_display(self):
        if self.current_song is not None:
            if self.current_song.state == 'stop':
                self.play_music()
        self.piece.cb_draw(cb=self.game_engine.draw_method, acb=self.audio_callback)

    def modify_state(self, pos, *kwargs):
        if 11 > pos[0] > 6:
            self.piece.move(RIGHT)
            self.refresh_display()
            self.audio_callback(audio_type='fx', audio_name='tick')
        elif -1 < pos[0] < 4:
            self.piece.move(LEFT)
            self.refresh_display()
            self.audio_callback(audio_type='fx', audio_name='tick')
        elif 3 < pos[0] < 7:
            self.piece.rotate()
            self.refresh_display()
            self.audio_callback(audio_type='fx', audio_name='rotate')
        else:
            pass

    def change_screen(self, name, angle="right"):
        self.__manager.transition.direction = angle
        last = str(self.__manager.current)
        try:
            self.__manager.current = name
        except Exception as e:
            self.__manager.current = last
        if last == 'settings':
            return True
        if last != name and name in ['menu', 'game']:
            self.piece.pause()
            if self.music_state:
                if self.current_song:
                    self.current_song.stop()
                    self.play_music()
            self.__knock = 0
        return True

    def widget_reset(self):
        self.game_board.reset()
        self.current_score = 'machine werkz'
        self.piece.pause()

    def get_speed(self, s):
        try:
            i = ["1.618", "1.2", "0.9", "0.5"].index(self.config.get('machinewerkz', 'fall_speed'))
        except ValueError:
            i = 4
        return ['Default', 'Intermediate', 'Advanced', 'Let me at em', "Custom"][i]

    def change_speed(self, t):
        a, b, c, d = (1.618, 1.2, 0.9, 0.5)
        try:
            res = {
                'Default': ('play whilst otherwise occupied', a),
                'Intermediate': ('not so slow', b),
                'Advanced': ('just chilling', c),
                'Let me at em': ('good luck', d)
            }[t]
            self.fall_speed = res[1]
            self.config.set('machinewerkz', 'fall_speed', res[1])
            self.config.write()
        except KeyError:
            return ""
        return "{}".format(res[0])

    def on_stop(self):
        self.empty_fx_bucket()
        if self.current_song:
            try:
                Logger.info('[MachineWerkz] stopping music')
                self.current_song.stop()
            except Exception as e:
                Logger.error('[MachineWerkz?] {}'.format(e))
        super(MachineWerkz, self).on_stop()

    def file_select(self, selection, p):
        available = []
        if len(selection) > 0:
            Logger.info("Selected : {}".format(selection))
            for _ in selection:
                if _[-4:] in ['.mp3', '.ogg']:
                    available.append(path.join(p, _))
        else:
            for _ in listdir(p):
                if _[-4:] in ['.mp3', '.ogg']:
                    available.append(path.join(p, _))
        if len(available) > 0:
            try:
                Logger.info('[MachineWerkz] stopping music')
                self.current_song.stop()
            except TypeError as e:
                Logger.error('[MachineWerkz?] {}'.format(e))
            self.music_state = False
            self.music_playlist = available
            self.music_played = [PLAYLIST]
            try:
                self.toggle_music()
            except TypeError:
                pass
            return True
        return False

    def reset_music(self):
        try:
            Logger.info('[MachineWerkz] stopping music')
            self.current_song.stop()
            sleep(.1)
        except Exception as e:
            Logger.error('[MachineWerkz?] {}'.format(e))
        self.music_playlist = [str(_) for _ in PLAYLIST]
        self.music_state = True
        self.music_played = []
        shuffle(self.music_playlist)
        if self.current_song.state == 'stop':
            self.toggle_music()


if __name__ == "__main__":
    MachineWerkz().run()
