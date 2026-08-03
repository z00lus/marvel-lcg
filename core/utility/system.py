import os

class System:

    @staticmethod
    def Run(cmd: str):
        os.system(cmd)

    @staticmethod
    def SetTitle(title: str):
        if os.name == 'nt':
            System.Run(f'title {title}')

    @staticmethod
    def Pause():
        System.Run('pause')

    @staticmethod
    def Sleep(secs: float):
        from time import sleep
        return sleep(secs)
