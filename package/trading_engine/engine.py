class TradingEngine:
    def __init__(self):
        self.running = False
        self.position = None

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def get_stats(self):
        return {"running": self.running, "position": self.position}

    def update(self):
        pass
