def convert_time(t: float) -> str:
    t = int(t)
    h = t // 3600
    m = (t % 3600) // 60
    s = t % 60
    return f"{h:02}:{m:02}:{s:02}"
