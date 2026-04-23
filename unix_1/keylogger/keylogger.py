import curses

def writeThatDown(typed):
    curses.curs_set(1) #show cursor
    typed.nodelay(False) #wait for input

    with open('log.txt','a') as observer:
        while(True):
            keyPressed = typed.getch()

            if keyPressed == 27:
                break

            try:
                char = chr(keyPressed)
            except ValueError:
                char = f"[{keyPressed}]"

            observer.write(char)
            typed.addstr(char)
            typed.refresh()
curses.wrapper(writeThatDown)