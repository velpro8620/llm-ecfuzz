import curses
import shutil
import threading
import time

stop = False

class Viewer:
    def __init__(self):
        self.box_width = None #
        self.cmd_thread = None # 
        self.data = 0

    def start(self):
        """
        
        """
        self.cmd_thread = threading.Thread(target=self.view_cmd) # 
        time.sleep(1) # 
        self.cmd_thread.start()

    def view_cmd(self):
        curses.wrapper(self.std_wrapper_cmd)

    def std_wrapper_cmd(self, stdscr): 
        stdscr.clear() # 
        curses.noecho() # 
        curses.curs_set(0) # 
        while True:
            time.sleep(0.2) # 
            contents = self.generate_contents() # 
            terminal_width, _ = shutil.get_terminal_size() # 
            box_width = max(int(terminal_width * 0.7), 80) 
            stdscr.resize(len(contents) + 4, box_width + 2) 
            stdscr.box() # 
            y = 1
            for y, content in enumerate(contents, start=1):
                stdscr.addstr(y, 1, content) # 
            stdscr.addstr(y + 2, 1, 'Press CTRL+C to stop the program early.')
            stdscr.refresh() # 
            if stop:
                # 
                stdscr.addstr(y + 2, 1, 'Test finished, press any key to exit ...', curses.A_BLINK)
                stdscr.getkey() # 
                break
        curses.curs_set(1) # 
        curses.echo() # 
        
    def generate_contents(self):
        contents = []
        t = time.time()
        contents.append(f"Current time is {t}")
        contents.append(f"Current count is {self.data}")
        self.data += 1

if __name__ == '__main__':
    viewer = Viewer()
    viewer.start()
