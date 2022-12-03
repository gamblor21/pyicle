from time import monotonic_ns
from math import sqrt, fabs
from random import randint

class Icicle():
    def __init__(self, grid, column, length = 20, color=(200,240,255), dribblePixel = 5, height = 0.174):
        self.color = color
        self.column = column
        self.pixel_pitch = 1 / 60
        self.gamma = 1.5
        self.g_const = 4.0#9.806
        self.ice_brightness = 20
        self._grid = grid
        self.length = length # Length of NeoPixel strip IN PIXELS
        self.dribblePixel = dribblePixel      # Index of pixel where dribble pauses before drop (0 to length-1)
        self.height= height    # Height IN METERS of dribblePixel above ground
        self.mode = "MODE_IDLE"        # One of the above states (MODE_IDLE, etc.)
        self.eventStartUsec = monotonic_ns() / 1000    # Starting time of current event
        self.eventDurationUsec = randint(500000, 2500000) # R(0.5-2.5) Duration of current event, in microseconds
        self.eventDurationReal = self.eventDurationUsec / 1000000 # Duration of current event, in seconds (float)
        self.splatStartUsec = 0   # Starting time of most recent "splat"
        self.splatDurationUsec = 0# Fade duration of splat
        self.pos = 0              # Position of self on prior frame
        self.idletimemax = 2200000
        self.growth_chance = 50 # chance out of 1000 icicle grows 1 pixel
        self.break_exponent = 1.7 # icicle breaks at len**break_exponent out of 1000
        self.max_dribble = 16 # auto break if the icicle gets longer

    def draw(self):
        t = monotonic_ns() / 1000 #Current time, in microseconds

        dtUsec = t - self.eventStartUsec; # Elapsed time, in microseconds, since start of current event
        dtReal = dtUsec / 1000000.0  # Elapsed time, in seconds

        #print(t, dtUsec, dtReal, self.mode)

        # Handle transitions between self states (oozing, dribbling, selfping, etc.)
        if dtUsec >= self.eventDurationUsec:               # Are we past end of current event?
            self.eventStartUsec += self.eventDurationUsec; # Yes, next event starts here
            dtUsec -= self.eventDurationUsec; # We're already this far into next event
            dtReal = dtUsec / 1000000.0

            if self.mode == "MODE_IDLE":
                self.mode = "MODE_OOZING" # Idle to oozing transition
                self.eventDurationUsec = randint(800000, 1200000) # 0.8 to 1.2 sec ooze
                self.eventDurationReal = self.eventDurationUsec / 1000000

            elif self.mode == "MODE_OOZING":
                if self.dribblePixel is not 0: #{ // If dribblePixel is nonzero...
                    self.mode = "MODE_DRIBBLING_1" # Oozing to dribbling transition
                    self.pos = self.dribblePixel
                    self.eventDurationUsec = 250000 + self.dribblePixel * randint(30000, 40000)
                    self.eventDurationReal = self.eventDurationUsec / 1000000
                else: # No dribblePixel...
                    self.pos = self.dribblePixel # Oozing to dripping transition
                    self.mode = "MODE_DRIPPING";
                    self.eventDurationReal = sqrt(self.height * 2.0 / self.g_const) # SCIENCE
                    self.eventDurationUsec = self.eventDurationReal * 1000000

            elif self.mode == "MODE_DRIBBLING_1":
                self.mode = "MODE_DRIBBLING_2" # Dripping 1st half to 2nd half transition
                self.eventDurationUsec = self.eventDurationUsec * 3 / 2 # Second half is 1/3 slower
                self.eventDurationReal = self.eventDurationUsec / 1000000

            elif self.mode == "MODE_DRIBBLING_2":
                self.mode = "MODE_DRIPPING" # Dribbling 2nd half to dripping transition
                # should icicle grow
                if self.growth_chance > randint(1,1000):
                    self.dribblePixel += 1

                self.pos = self.dribblePixel
                self.eventDurationReal = sqrt(self.height * 2.0 / self.g_const) # SCIENCE
                self.eventDurationUsec = self.eventDurationReal * 1000000

            elif self.mode == "MODE_DRIPPING":
                self.mode = "MODE_IDLE" # Dripping to idle transition
                self.eventDurationUsec = randint(500000, self.idletimemax) # Idle for 0.5 to 1.2 seconds
                self.eventDurationReal = self.eventDurationUsec / 1000000
                # breaking icicle
                if self.dribblePixel**self.break_exponent > randint(1,1000) or self.dribblePixel > self.max_dribble:
                    self.dribblePixel = randint(1, self.dribblePixel-1)
                    #print("Icicle ", self.column, " broke at ", self.dribblePixel)

                self.splatStartUsec    = self.eventStartUsec # Splat starts now!
                self.splatDurationUsec = randint(900000, 1100000)

    # Render drip state to NeoPixels...
#      // Draw icycles if ICE_BRIGHTNESS is setpixel
        if self.ice_brightness > 0:
            x = pow(self.ice_brightness * 0.01, self.gamma)
            for d in range (0, self.dribblePixel+1):
                self.setpixel(d, x);

        if self.mode == "MODE_IDLE":
            pass

        elif self.mode == "MODE_OOZING":
            x = dtReal / self.eventDurationReal # 0.0 to 1.0 over ooze interval
            x = sqrt(x) # Perceived area increases linearly
            if self.ice_brightness > 0:
                x = (self.ice_brightness * 0.01) + x * (100 - self.ice_brightness) * 0.01
            x = pow(x, self.gamma)
            self.setpixel(0, x)

        elif self.mode == "MODE_DRIBBLING_1":
            # Point b moves from first to second pixel over event time
            x = dtReal / self.eventDurationReal # 0.0 to 1.0 during move
            x = 3 * x * x - 2 * x * x * x # Easing function: 3*x^2-2*x^3 0.0 to 1.0
            self.dripDraw(self.column, 0.0, x * self.dribblePixel, False)

        elif self.mode == "MODE_DRIBBLING_2":
            # Point a moves from first to second pixel over event time
            x = dtReal / self.eventDurationReal # 0.0 to 1.0 during move
            x = 3 * x * x - 2 * x * x * x # Easing function: 3*x^2-2*x^3 0.0 to 1.0
            self.dripDraw(self.column, x * self.dribblePixel, self.dribblePixel, False)

        elif self.mode == "MODE_DRIPPING":
            x = 0.5 * self.g_const * dtReal * dtReal # Position in meters
            x = self.dribblePixel + x / self.pixel_pitch # Position in pixels
            self.dripDraw(self.column, self.pos, x, True)
            self.pos = x

        dtUsec = t - self.splatStartUsec # Elapsed time, in microseconds, since start of splat
        if dtUsec < self.splatDurationUsec:
            x = 1.0 - sqrt(dtUsec / self.splatDurationUsec)
            x = pow(x, self.gamma)
            self.setpixel(self.length-1, x);

# This "draws" a drip in the NeoPixel buffer...zero to peak brightness
# at center and back to zero. Peak brightness diminishes with length,
# and drawn dimmer as pixels approach strand length.
    def dripDraw(self, dNum, a, b, fade):
        #print("DD", a, b)
        if a > b:  # Sort a,b inputs if needed so a<=b
            t = a
            a = b
            b = t

        #Find range of pixels to draw. If first pixel is off end of strand,
        #nothing to draw. If last pixel is off end of strand, clip to strand length.
        firstPixel = int(a)
        if firstPixel >= self.length:
            return
        lastPixel = int(b) + 1
        if lastPixel >= self.length:
            lastPixel = self.length - 1

        center = (a + b) * 0.5    # Midpoint of a-to-b
        midrange = center - a + 1.0 # Distance from center to a, plus 1 pixel
        x = 0.0
        for i in range(firstPixel, lastPixel):
            x = fabs(center - i) # Pixel distance from center point
            if x < midrange:            # Inside drip
                x = (midrange - x) / midrange;         # 0.0 (edge) to 1.0 (center)
                if(fade):
                    dLen = self.length - self.dribblePixel # Length of drip
                    if dLen > 0:  # Scale x by 1.0 at top to 1/3 at bottom of drip
                        dPixel = i - self.dribblePixel # Pixel position along drip
                        x *= 1.0 - (dPixel / dLen * 0.66)
            else:
                x = 0.0;

            # Upper pixels may be partially lit for an icycle effect
            if self.ice_brightness > 0:
                if i <= self.dribblePixel:
                  x = (self.ice_brightness * 0.01) + x * (100 - self.ice_brightness) * 0.01
            x = pow(x, self.gamma)
            self.setpixel(i, x)

    # Set one pixel to a given brightness level (0.0 to 1.0)
    def setpixel(self, pixel, brightness):
        color = tuple([(brightness+0.0) * x for x in self.color])
        #print("Set pixel", pixel, brightness, color)
        #self._grid[self.column, int(pixel)] = color
        #print(self.column*20, int(pixel), [self.column*20 + int(pixel)])
        self._grid[self.column*20 + int(pixel)] = color
