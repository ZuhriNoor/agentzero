
from ics import Calendar, Event
import arrow

def test_ics_timezone():
    print("Testing ICS Timezone Behavior...")
    
    # constant naive time string
    naive_str = "2026-02-15 10:00:00"
    
    c = Calendar()
    e = Event()
    e.name = "Naive Test"
    e.begin = naive_str
    c.events.add(e)
    
    serialized = c.serialize()
    print(f"\n[Input]: {naive_str}")
    for line in serialized.splitlines():
        if "DTSTART" in line:
            print(f"[Output Line]: {line}")
            if "Z" in line:
                print("-> SAVED AS UTC (Z suffix present)")
            else:
                print("-> SAVED AS FLOATING (No Z suffix)")

    # constant aware time string (with offset)
    aware_str = "2026-02-15 10:00:00+05:30"
    c2 = Calendar()
    e2 = Event()
    e2.name = "Aware Test"
    e2.begin = aware_str
    c2.events.add(e2)
    
    serialized2 = c2.serialize()
    print(f"\n[Input]: {aware_str}")
    for line in serialized2.splitlines():
        if "DTSTART" in line:
            print(f"[Output Line]: {line}")

if __name__ == "__main__":
    test_ics_timezone()
