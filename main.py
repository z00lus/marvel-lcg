from engine import Engine

if __name__ == "__main__":
    initialized = False

    try:
        initialized = Engine.Initialize()
        if initialized:
            Engine.EngineRun()
    except KeyboardInterrupt:
        pass
    finally:
        if initialized:
            Engine.Shutdown()
