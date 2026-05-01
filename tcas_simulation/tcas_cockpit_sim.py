import sys
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
                          QPolygonF, QTransform)

# =============================================================================
# TCAS II COCKPIT DISPLAY SIMULATION
# Simulates two aircraft on a converging flight path and demonstrates
# how a real TCAS II system would issue Traffic Advisories (TA) and
# Resolution Advisories (RA) based on range, vertical separation, and
# time to closest point of approach (CPA).
# =============================================================================


# ─── TCAS Logic ───────────────────────────────────────────────────────────────

class Aircraft:
    """Represents an aircraft with position, altitude, heading, and speed."""
    def __init__(self, name, x, y, altitude, heading, speed):
        self.name     = name
        self.x        = x         # horizontal position in nautical miles
        self.y        = y         # vertical position in nautical miles
        self.altitude = altitude  # altitude in feet
        self.heading  = heading   # heading in degrees (0 = north)
        self.speed    = speed     # speed in knots

    def update(self, dt):
        """Move the aircraft forward based on its heading and speed over time dt (seconds)."""
        rad      = math.radians(self.heading)
        dist     = self.speed * (dt / 3600)  # convert knots to nm per second
        self.x  += dist * math.sin(rad)
        self.y  += dist * math.cos(rad)


def range_nm(a, b):
    """Calculate horizontal distance between two aircraft in nautical miles."""
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def vert_sep(a, b):
    """Calculate vertical separation between two aircraft in feet."""
    return abs(a.altitude - b.altitude)

def closure_rate(a, b):
    """
    Estimate how fast two aircraft are closing in on each other (knots).
    Positive value means they are converging.
    """
    r1   = range_nm(a, b)
    rad1 = math.radians(a.heading)
    rad2 = math.radians(b.heading)
    d1, d2 = a.speed / 3600, b.speed / 3600
    # Project both aircraft one second forward to estimate new range
    x1p = a.x + d1 * math.sin(rad1)
    y1p = a.y + d1 * math.cos(rad1)
    x2p = b.x + d2 * math.sin(rad2)
    y2p = b.y + d2 * math.cos(rad2)
    r2  = math.sqrt((x1p - x2p)**2 + (y1p - y2p)**2)
    return (r1 - r2) * 3600  # convert back to knots

def time_to_cpa(a, b):
    """
    Estimate time in seconds until closest point of approach (CPA).
    Returns infinity if aircraft are not converging.
    """
    cr = closure_rate(a, b)
    r  = range_nm(a, b)
    if cr <= 0:
        return float('inf')
    return (r / cr) * 3600

def advisory_status(rng, vs, tcpa):
    """
    Determine TCAS advisory level based on three thresholds:
      - Range in nautical miles
      - Vertical separation in feet
      - Time to closest point of approach in seconds

    All three conditions must be met simultaneously to trigger each level.
    Matches real TCAS II Version 7.1 logic.
    """
    if rng < 5 and vs < 600 and tcpa < 25:
        return "RA"         # Resolution Advisory - pilot must maneuver now
    elif rng < 6 and vs < 850 and tcpa < 40:
        return "TA"         # Traffic Advisory - pilot should be aware
    elif rng < 6:
        return "PROXIMATE"  # Close traffic but not yet a threat
    return "OTHER"          # No advisory - normal flight


# ─── Radar Display Widget ─────────────────────────────────────────────────────

class RadarDisplay(QWidget):
    """
    Custom widget that draws a TCAS cockpit radar scope.
    Own aircraft sits at center. Intruder moves relative to it.
    Intruder symbol changes shape and color based on advisory state.
    """
    RANGE_NM = 12  # display range in nautical miles

    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 400)
        self.ac1    = None
        self.ac2    = None
        self.status = "OTHER"

    def set_aircraft(self, ac1, ac2, status):
        """Update aircraft positions and advisory status, then redraw."""
        self.ac1    = ac1
        self.ac2    = ac2
        self.status = status
        self.update()  # triggers paintEvent

    def nm_to_px(self, nx, ny, cx, cy, scale):
        """Convert nautical mile coordinates to pixel coordinates on screen."""
        px = cx + nx * scale
        py = cy - ny * scale  # invert y so north is up
        return px, py

    def paintEvent(self, event):
        """Draw the radar scope every time the widget updates."""
        if not self.ac1:
            return

        p      = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h   = self.width(), self.height()
        cx, cy = w / 2, h / 2
        scale  = min(w, h) / 2 / self.RANGE_NM * 0.88

        # Black radar background
        p.fillRect(0, 0, w, h, QColor(10, 15, 25))

        # Draw range rings at 3, 6, 9, and 12 nm
        for rings in [3, 6, 9, 12]:
            r = rings * scale
            p.setPen(QPen(QColor(40, 80, 60), 1, Qt.DotLine))
            p.drawEllipse(QPointF(cx, cy), r, r)
            p.setPen(QPen(QColor(60, 120, 80), 1))
            p.setFont(QFont("Courier", 9))
            p.drawText(int(cx + r + 3), int(cy - 3), f"{rings}nm")

        # Draw crosshairs through center
        p.setPen(QPen(QColor(40, 80, 60), 1))
        p.drawLine(int(cx), int(cy - min(w,h)/2*0.9), int(cx), int(cy + min(w,h)/2*0.9))
        p.drawLine(int(cx - min(w,h)/2*0.9), int(cy), int(cx + min(w,h)/2*0.9), int(cy))

        # Draw own aircraft as white triangle at center
        self._draw_own_aircraft(p, cx, cy)

        # Calculate intruder position relative to own aircraft
        rx = self.ac2.x - self.ac1.x
        ry = self.ac2.y - self.ac1.y
        ix, iy = self.nm_to_px(rx, ry, cx, cy, scale)

        # If intruder is outside display range, clamp it to edge of scope
        dist_px = math.sqrt((ix - cx)**2 + (iy - cy)**2)
        max_r   = min(w, h) / 2 * 0.88
        if dist_px > max_r:
            angle = math.atan2(iy - cy, ix - cx)
            ix    = cx + max_r * math.cos(angle)
            iy    = cy + max_r * math.sin(angle)

        # Altitude difference tag (+/- hundreds of feet)
        alt_diff = int((self.ac2.altitude - self.ac1.altitude) / 100)
        self._draw_intruder(p, ix, iy, alt_diff)

        p.end()

    def _draw_own_aircraft(self, p, cx, cy):
        """Draw own aircraft as a white hollow triangle at radar center."""
        size = 10
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.setBrush(Qt.NoBrush)
        pts = QPolygonF([
            QPointF(cx,            cy - size),
            QPointF(cx - size*0.7, cy + size*0.7),
            QPointF(cx,            cy + size*0.3),
            QPointF(cx + size*0.7, cy + size*0.7),
        ])
        p.drawPolygon(pts)

    def _draw_intruder(self, p, ix, iy, alt_diff):
        """
        Draw the intruder symbol based on current advisory status.
        Matches real TCAS II cockpit display symbols:
          RA  -> filled red square with descent arrow
          TA  -> filled yellow circle
          PROXIMATE -> filled cyan diamond
          OTHER -> hollow gray diamond
        """
        s    = self.status
        size = 12

        if s == "RA":
            # Red filled square = Resolution Advisory
            color = QColor(220, 50, 50)
            p.setPen(QPen(color, 2))
            p.setBrush(QBrush(color))
            p.drawRect(int(ix - size/2), int(iy - size/2), size, size)
            # White downward arrow indicating descend guidance
            p.setPen(QPen(QColor(255, 255, 255), 2))
            p.drawLine(int(ix), int(iy + size), int(ix), int(iy + size + 14))
            p.drawLine(int(ix - 5), int(iy + size + 8), int(ix), int(iy + size + 14))
            p.drawLine(int(ix + 5), int(iy + size + 8), int(ix), int(iy + size + 14))

        elif s == "TA":
            # Yellow filled circle = Traffic Advisory
            color = QColor(230, 180, 0)
            p.setPen(QPen(color, 2))
            p.setBrush(QBrush(color))
            p.drawEllipse(QPointF(ix, iy), size/2, size/2)

        elif s == "PROXIMATE":
            # Cyan filled diamond = close traffic, not yet a threat
            color = QColor(0, 200, 200)
            p.setPen(QPen(color, 2))
            p.setBrush(QBrush(color))
            diamond = QPolygonF([
                QPointF(ix,          iy - size/2),
                QPointF(ix + size/2, iy),
                QPointF(ix,          iy + size/2),
                QPointF(ix - size/2, iy),
            ])
            p.drawPolygon(diamond)

        else:
            # Gray hollow diamond = other traffic, no advisory
            color = QColor(180, 180, 180)
            p.setPen(QPen(color, 1.5))
            p.setBrush(Qt.NoBrush)
            diamond = QPolygonF([
                QPointF(ix,          iy - size/2),
                QPointF(ix + size/2, iy),
                QPointF(ix,          iy + size/2),
                QPointF(ix - size/2, iy),
            ])
            p.drawPolygon(diamond)

        # Draw altitude tag next to intruder (e.g. +03 means 300ft above)
        sign = "+" if alt_diff >= 0 else ""
        p.setPen(QPen(color, 1))
        p.setFont(QFont("Courier", 9, QFont.Bold))
        p.drawText(int(ix + size), int(iy - 4), f"{sign}{alt_diff:02d}")


# ─── Main Window ──────────────────────────────────────────────────────────────

class TCASWindow(QMainWindow):
    """
    Main application window.
    Manages the simulation loop, aircraft state, and UI updates.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TCAS II Cockpit Display Simulation")
        self.setMinimumSize(820, 560)
        self.setStyleSheet("background-color: #0a0f19; color: #c0d0c0;")

        self._reset_sim()   # initialize aircraft and state variables
        self._build_ui()    # build the window layout

        # Timer drives the simulation - fires every 200ms
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)

    def _reset_sim(self):
        """
        Initialize both aircraft and reset all simulation state.
        N123AA = own aircraft, heading north at FL350
        N456BB = intruder, heading south at FL353 (head-on converging)
        """
        self.ac1         = Aircraft("N123AA", 0.0, 0.0,  35000, 0,   450)
        self.ac2         = Aircraft("N456BB", 0.2, 10.0, 35300, 180, 430)
        self.t           = 0        # elapsed time in ticks
        self.ra_issued   = False    # tracks if RA has fired
        self.coc_issued  = False    # tracks if clear of conflict has fired
        self.prev_status = "OTHER"  # previous advisory state for change detection
        self.log         = []       # event log entries
        self.running     = False    # simulation running flag

    def _build_ui(self):
        """Build the main window layout with radar on the left and data panel on the right."""
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(16)
        root.setContentsMargins(16, 16, 16, 16)

        # ── Left side: radar display ──
        left = QVBoxLayout()
        self.radar = RadarDisplay()
        self.radar.set_aircraft(self.ac1, self.ac2, "OTHER")
        left.addWidget(self.radar)

        rl = QLabel("Range: 12 nm")
        rl.setAlignment(Qt.AlignCenter)
        rl.setStyleSheet("color: #60a060; font: 10px Courier;")
        self.range_label = rl
        left.addWidget(rl)
        root.addLayout(left, 2)

        # ── Right side: advisory banner, data readouts, event log, buttons ──
        right = QVBoxLayout()
        right.setSpacing(10)

        # Advisory banner changes color based on current state
        self.advisory_banner = QLabel("NO ADVISORY")
        self.advisory_banner.setAlignment(Qt.AlignCenter)
        self.advisory_banner.setFont(QFont("Courier", 18, QFont.Bold))
        self.advisory_banner.setFixedHeight(60)
        self.advisory_banner.setStyleSheet(
            "background: #1a2a1a; color: #60d060; border: 1px solid #2a4a2a; border-radius: 6px;")
        right.addWidget(self.advisory_banner)

        # Live data readouts grid
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background: #0d1520; border: 1px solid #1a3a2a; border-radius: 6px;")
        grid = QGridLayout(grid_frame)
        grid.setSpacing(6)
        grid.setContentsMargins(12, 12, 12, 12)

        def lbl(text, bold=False):
            l = QLabel(text)
            l.setFont(QFont("Courier", 11, QFont.Bold if bold else QFont.Normal))
            l.setStyleSheet("color: #80b080; background: transparent; border: none;")
            return l

        def val(text="--"):
            l = QLabel(text)
            l.setFont(QFont("Courier", 11))
            l.setStyleSheet("color: #e0f0e0; background: transparent; border: none;")
            return l

        # Add each data field to the grid
        grid.addWidget(lbl("Time"),     0, 0); self.v_time  = val(); grid.addWidget(self.v_time,  0, 1)
        grid.addWidget(lbl("Range"),    1, 0); self.v_range = val(); grid.addWidget(self.v_range, 1, 1)
        grid.addWidget(lbl("Vert sep"), 2, 0); self.v_vs    = val(); grid.addWidget(self.v_vs,    2, 1)
        grid.addWidget(lbl("CPA"),      3, 0); self.v_cpa   = val(); grid.addWidget(self.v_cpa,   3, 1)
        grid.addWidget(lbl("Own alt"),  4, 0); self.v_alt1  = val(); grid.addWidget(self.v_alt1,  4, 1)
        grid.addWidget(lbl("Int alt"),  5, 0); self.v_alt2  = val(); grid.addWidget(self.v_alt2,  5, 1)
        right.addWidget(grid_frame)

        # Event log shows timestamped advisory events
        log_label = QLabel("Event Log")
        log_label.setFont(QFont("Courier", 10))
        log_label.setStyleSheet("color: #507050;")
        right.addWidget(log_label)

        self.log_box = QLabel("Waiting...")
        self.log_box.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.log_box.setFont(QFont("Courier", 10))
        self.log_box.setStyleSheet(
            "background: #080e18; color: #70a070; border: 1px solid #1a3a2a; "
            "border-radius: 4px; padding: 8px;")
        self.log_box.setWordWrap(True)
        self.log_box.setMinimumHeight(120)
        right.addWidget(self.log_box)

        right.addStretch()

        # Start/Reset buttons
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("START")
        self.btn_reset = QPushButton("RESET")
        for btn in [self.btn_start, self.btn_reset]:
            btn.setFont(QFont("Courier", 11, QFont.Bold))
            btn.setFixedHeight(38)
            btn.setStyleSheet(
                "QPushButton { background: #1a3a2a; color: #80e080; border: 1px solid #2a6a3a; border-radius: 5px; }"
                "QPushButton:hover { background: #2a5a3a; }"
                "QPushButton:pressed { background: #0a2a1a; }")
        self.btn_start.clicked.connect(self._toggle)
        self.btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_reset)
        right.addLayout(btn_row)

        root.addLayout(right, 1)

    def _toggle(self):
        """Start or pause the simulation timer."""
        if self.running:
            self.timer.stop()
            self.running = False
            self.btn_start.setText("RESUME")
        else:
            self.timer.start(200)  # tick every 200ms
            self.running = True
            self.btn_start.setText("PAUSE")

    def _reset(self):
        """Stop the simulation and reset everything back to initial state."""
        self.timer.stop()
        self._reset_sim()
        self.btn_start.setText("START")
        self.radar.set_aircraft(self.ac1, self.ac2, "OTHER")
        self._update_panel("OTHER", 10.0, 300, float('inf'))
        self.log_box.setText("Waiting...")
        self.advisory_banner.setText("NO ADVISORY")
        self.advisory_banner.setStyleSheet(
            "background: #1a2a1a; color: #60d060; border: 1px solid #2a4a2a; border-radius: 6px;")

    def _tick(self):
        """
        Main simulation step - called every 200ms by the timer.
        Calculates current TCAS values, checks for advisory state changes,
        applies vertical maneuver if RA is active, and updates the display.
        """
        # Calculate current separation metrics
        rng    = range_nm(self.ac1, self.ac2)
        vs     = vert_sep(self.ac1, self.ac2)
        tcpa   = time_to_cpa(self.ac1, self.ac2)
        status = advisory_status(rng, vs, tcpa)

        # Log Traffic Advisory when it first fires
        if status == "TA" and self.prev_status not in ("TA", "RA"):
            self.log.append(f"T+{self.t:03d}s  TRAFFIC ADVISORY  {rng:.1f}nm")

        # Log Resolution Advisory when it first fires
        if status == "RA" and not self.ra_issued:
            self.ra_issued = True
            self.log.append(f"T+{self.t:03d}s  RESOLUTION ADVISORY  {rng:.1f}nm")

        # Apply vertical maneuver to own aircraft while RA is active
        # Climb if intruder is below, descend if intruder is above
        if self.ra_issued and not self.coc_issued:
            if self.ac2.altitude <= self.ac1.altitude:
                self.ac1.altitude += 1500 * (0.2 / 60)  # climb at 1500 fpm
            else:
                self.ac1.altitude -= 1500 * (0.2 / 60)  # descend at 1500 fpm

        # Log Clear of Conflict once separation is restored
        if self.ra_issued and not self.coc_issued and vs >= 700 and status != "RA":
            self.coc_issued = True
            self.log.append(f"T+{self.t:03d}s  CLEAR OF CONFLICT  {vs:.0f}ft sep")

        # Update previous status for change detection next tick
        self.prev_status = status

        # Refresh UI
        self._update_panel(status, rng, vs, tcpa)
        self.radar.set_aircraft(self.ac1, self.ac2, status)
        self.log_box.setText("\n".join(self.log[-6:]) if self.log else "Waiting...")

        # Move both aircraft forward one time step
        self.ac1.update(0.2)
        self.ac2.update(0.2)
        self.t += 1

        # Auto-stop once aircraft are well clear and no advisory is active
        if self.t > 60 and rng > 8 and status == "OTHER":
            self.timer.stop()
            self.running = False
            self.btn_start.setText("DONE")
            self.log.append(f"T+{self.t:03d}s  SIMULATION COMPLETE")
            self.log_box.setText("\n".join(self.log[-6:]))

    def _update_panel(self, status, rng, vs, tcpa):
        """Update all data readouts and change advisory banner color based on status."""
        self.v_time.setText(f"T+{self.t:03d}s")
        self.v_range.setText(f"{rng:.2f} nm")
        self.v_vs.setText(f"{vs:.0f} ft")
        self.v_cpa.setText(f"{tcpa:.1f}s" if tcpa != float('inf') else "N/A")
        self.v_alt1.setText(f"{int(self.ac1.altitude):,} ft")
        self.v_alt2.setText(f"{int(self.ac2.altitude):,} ft")

        # Color scheme for each advisory state
        STYLES = {
            "RA":        ("RESOLUTION ADVISORY", "#cc2222", "#ff6060"),
            "TA":        ("TRAFFIC  ADVISORY",   "#aa7700", "#ffcc00"),
            "PROXIMATE": ("PROXIMATE TRAFFIC",   "#006666", "#00cccc"),
            "OTHER":     ("NO ADVISORY",         "#1a2a1a", "#60d060"),
        }
        text, bg, fg = STYLES.get(status, STYLES["OTHER"])
        self.advisory_banner.setText(text)
        self.advisory_banner.setStyleSheet(
            f"background: {bg}; color: {fg}; border: 1px solid {fg}; border-radius: 6px;")
        self.range_label.setText("Display range: 12 nm")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TCASWindow()
    win.show()
    sys.exit(app.exec_())