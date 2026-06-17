
COLOR_SET_STATUS = 20460
COLOR_RESET_STATUS = 65535



class Nextion():
    def __init__(self):
        self.color_set_status = 20460
        self.color_reset_status = 65535
        
        self.active_page = 0
        
        self.page_settings = {
            "Manual mode:" : 0, 
            "Panel 1" : 0,
            "Panel 2" : 0,
            "Main module:" : 0,
            "Conn module:" : 0,
            "Live module:" : 0,
            "Energ module:" : 0,
            "t1": self.color_set_status,
            "t2": self.color_reset_status,
            "t3": self.color_reset_status,
            "t4": self.color_reset_status,
        }
        
        self.page_color = {
            "Power:": 0, 
            "Red:" : 0,
            "Green:" : 0,
            "Blue:" : 0,
            "Main color:" : 0,
            "Conn color:" : 0,
            "Live color:" : 0,
            "Energ color:" : 0,
            "t1": self.color_set_status,
            "t2": self.color_reset_status,
            "t3": self.color_reset_status,
            "t4": self.color_reset_status,
        }



    def _parsingNextionPacket(self, pack: str) -> dict:
        pages = (self.page_settings, self.page_color)
        for page in range(len(pages)):
            for key in pages[page].keys():
                if key in pack:
                    self.active_page = 0 if page == 0 else 1
                    return {key: int(pack[-1])}

        return None
    
    def updateStateNextion(self, pack: str) -> bool:
        new_state = self._parsingNextionPacket(pack)
        if self.active_page == 0:
            pass
        elif self.active_page == 1:
            pass
        else:
            return False
    
    
    def setPametersNextion(self, name_vidget:str, param: str, val) -> None:
        pass


            
    

if __name__ == "__main__":
    n = Nextion()
    print(n.parsingNextionPacket("Manual mode:1"))
    # print(parsingNextionPacket("Manual mode:1", PAGES))
    pass