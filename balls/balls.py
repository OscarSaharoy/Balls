import pygame, random, math, numpy, sys, tkinter, gooey
from tkinter.font import Font


pygame.init()

info = pygame.display.Info()

SP    = info.current_h // 50  # measurement unit

x_res = SP * 25   # Width of display
y_res = SP * 25   # Height of display

# Palette

white = (255, 255, 255)
black = (  0,   0,   0)
leaf  = ( 30, 255,  30)
jade  = (100, 150, 100)
blue  = ( 34, 238, 255)
gray  = ( 40,  60,  70)

class Balls(object):

    def __init__(self):

        data       = Data()

        data.n     = 70     # number of balls
        data.rest  = 1      # restitution of system
        data.g     = 0.005  # acceleration due to gravity in pixels per frame
        data.v0    = 1      # maximum initial velocity of balls
        data.r = r = SP//2  # radius of balls
        data.d     = 2*r    # diameter of balls
        data.fps   = 60     # framerate
        data.f_len = 100    # length of fade for ball impact colour
 
        data.pos   = numpy.random.rand(data.n,2) * numpy.array([[x_res-data.d, y_res-data.d]]) + data.d # position of balls - randomised at start
        data.vel   = numpy.random.rand(data.n,2) * data.v0 - data.v0/2 # velocity of balls
        data.mass  = numpy.ones(200) # masses of balls
        data.val   = numpy.zeros(200) # stores colour value data - colours brightest after collision and then fade

        data.hex   = '#22eeff' # hex of base colour - cyan default
        data.rhue  = numpy.random.rand(200,3) # random colours with different hues
        data.rgrey = numpy.random.rand(200,1).repeat(3,axis=1) # random grays
        data.hue_v = 0.5 # amount of hue variation
        data.val_v = 1.0 # amount of value variation
        data.fade  = True # controls whether balls get colour on impact and then fade or have constant colour

        data.closed = False # True if settings panel is closed

        data.last_outside = numpy.zeros([data.n,2]) == 1 # stores balls which were outside screen last timestep - starts all False

        self.data  = data

        # initialise window for drawing
        self.surface = pygame.display.set_mode((x_res,y_res))
        pygame.display.set_caption(' Balls')

        # setting favicon
        icon = pygame.image.load(r'assets/favicon.png')
        pygame.display.set_icon(icon)

        # initialising tkinter setitngs panel
        self.panel = Panel(self, self.data)

        # binding certain events in the settings panel to get the values of the vairables in it 
        self.panel.bind('<B1-Motion>',       self.panel.get_vars)
        self.panel.bind('<ButtonRelease-1>', self.panel.get_vars)
        self.panel.bind('<Return>',          self.panel.get_vars)

        # call main loop
        self.mainloop()


    def draw(self):

        data = self.data

        self.surface.fill(white) # clear screen

        # new ball position is previous position + velocity
        data.pos += data.vel

        # calculate random colours according to variables set

        hue         = ((data.hue_v*data.rhue + (1-data.hue_v)*data.rgrey) * 0.5 + 0.5)
        base_colour = (int('0x'+data.hex[1:3], 0), int('0x'+data.hex[3:5], 0), int('0x'+data.hex[5:7], 0))
        data.tone   = (data.val_v*hue + (1-data.val_v)) * numpy.array([base_colour]) # randomise colours

        # draw blue filling and black outline for each ball at its coords
        for i,point in enumerate(data.pos):

            # calculate effect of colour fade on colour of ball
            tone = data.tone[i]*data.val[i] if data.fade else data.tone[i]

            pygame.draw.circle(self.surface, tone,  [int(point[0]),int(point[1])], data.r, 0)
            pygame.draw.circle(self.surface, black, [int(point[0]),int(point[1])], data.r, 1)


    def gravity(self):

        data = self.data

        # gravity array is data.g in each of the y components for each ball
        grav      = numpy.ones([data.n,2]) * numpy.array([[0, 1]]) * data.g

        # add the velocity from gravity to the current velocity
        data.vel += grav


    def restrict(self, pos, res):

        data = self.data

        # limits pos to between data.r and res-data.r - makes sure ball is completely inside rendered area
        return float(sorted([ data.r, pos, res-data.r ])[1])


    def bounce(self):

        data = self.data

        # finds which balls are outside the screen and puts true in these slots
        outside_greater = data.pos >= numpy.array([[ x_res-data.r, y_res-data.r ]])
        outside_lesser  = data.pos <= numpy.array([[       data.r,       data.r ]])

        # OR together last 2 arrays to get all balls outside screen in 1 array
        outside   = outside_greater | outside_lesser

        # return balls which are currently outside AND not outside in the last timestep - balls shouldnt bounce twice or they get stuck
        outside   = outside & ~data.last_outside

        # store which balls are currently outside to compare to next timestep
        data.last_outside = outside

        # convert boolean values to 1 for balls which are inside and -1 for outside, adjusted byt the restitution
        to_bounce = outside * (-1-data.rest) + 1

        # multiply velocities by to_bounce to flip those which need to be
        data.vel *= to_bounce

        # vectorise self.restrict so it can be applied to an array
        restrict  = numpy.vectorize(self.restrict)

        # make sure all balls are inside screen
        data.pos  = restrict(data.pos, x_res)


    def collide(self):

        data = self.data

        # collisions keeps track of which collisions have already been computed
        collisions = [[] for _ in range(data.n)]

        for i1, ball_pos in enumerate(data.pos):

            # calculate distance from current ball to all other balls
            pos_translate = (data.pos - ball_pos)**2
            dist  = numpy.sum(pos_translate, axis=1)**0.5

            # they collide if the distance is less than 2 times the radius but not 0 - corresponds to current ball
            hit   = (dist <= data.r*2) & (dist != 0.0)

            # get indexes of balls which are colliding with current
            index = numpy.nonzero(hit)[0]

            for i2 in index:

                # record that i1 has collided with i2
                collisions[i1].append(i2)

                # if this collision has already been computed from other ball then skip it
                if i1 in collisions[i2]:
                    continue

                # compute resultant velocities from collision
                self.compute(i1, i2)

                # set 1 in data.val to make colour bright
                data.val[i1] = data.val[i2] = 1.0


    def rotation_matrix(self, th):

        # returns matrix which rotates vector around origin anticlockwise by theta

        sin, cos = numpy.sin, numpy.cos

        return numpy.matrix([[cos(th), -sin(th)],
                             [sin(th),  cos(th)]])


    def compute(self, i1, i2):

        data = self.data

        # find velocities, positions and masses of balls
        x1, x2 = data.pos[i1],  data.pos[i2]
        v1, v2 = data.vel[i1],  data.vel[i2]
        m1, m2 = data.mass[i1], data.mass[i2]

        # e is the restitution of the system and de is the postion delta of the 2 balls
        e      = -data.rest
        de     = x2 - x1

        # translate velocities to frame of reference of ball 2 and find angle of line of centres
        v1r    = v1 - v2
        th     = numpy.arctan2(de[1], de[0])

        # set value for intensity of colour dependant on impact speed
        # v1rm   = (v1r[0]**2 + v1r[1]**2) ** 0.5
        # val    = min(v1rm/3, 1.0)
        # self.val[i1] = self.val[i2] = val

        # make rotation matrices for + and - line of centres and then rotate relative velocity of balls
        rot    = self.rotation_matrix(-th)
        m_rot  = self.rotation_matrix(th)
        v1rr   = numpy.matmul(rot, v1r)

        # get relative rotated vx and vy of ball 1
        vx, vy = v1rr[0,0], v1rr[0,1]

        # ~~~ todo replace with matrix multiplication ~~~

        # calculate new rotated relative velocities by conservation of momentum and restitution
        v1rrn  = [ vx * (m1+e*m1)/(m1+m2) , vy ]
        v2rrn  = [ vx * (m1-e*m2)/(m1+m2) ,  0 ]

        # rotate velocities back to normal coordinate system
        v1rn   = numpy.matmul(m_rot, v1rrn)
        v2rn   = numpy.matmul(m_rot, v2rrn)

        # translate velocities to aboslute velocity
        v1n    = v1rn + v2
        v2n    = v2rn + v2

        # overwite current velocities with computed velocities
        data.vel[i1]  = numpy.array(v1n)[0]
        data.vel[i2]  = numpy.array(v2n)[0]

        # ~~~ todo improve next part ~~~

        # calculate distance between balls - need to move balls apart so they are no longer colliding
        mde    = (de[0]**2 + de[1]**2)**0.5

        # find fraction of 2*radius to move - divided by 4 as each ball moves 1 quarter of this distance
        fr     = (data.r*2 - mde) / data.r*2 / 4

        # calculate move in x and y
        m      = [fr * de[0], fr * de[1]]

        # move balls by this amount
        data.pos[i1] -= m
        data.pos[i2] += m


    def evolve_fade(self):

        data = self.data

        # reduce self.val in an exponential decay making ball colour fade over time

        decay_const = 1-1/data.f_len
   
        data.val    = data.val*decay_const + 0.2*(1-decay_const)


    def energy(self):

        data = self.data

        # sums kinetic energy of balls and prints it

        energy = sum([0.5*(vx**2 + vy**2)*0.5 for (vx,vy) in data.vel])

        print(energy)


    def n_balls(self):

        data = self.data

        # difference in number of balls
        diff = data.n - data.pos.shape[0]

        # truncates relevant arrays if decreasing number of balls
        if diff < 0:

            data.pos  = data.pos[ :data.n]
            data.vel  = data.vel[ :data.n]

            data.last_outside = data.last_outside[:data.n]

        # creates new random values and appends them onto existing arrays if increasing number of balls
        elif diff > 0:

            newpos    = numpy.random.rand(diff,2) * numpy.array([[x_res-data.d, y_res-data.d]]) + data.d
            newvel    = numpy.random.rand(diff,2) * data.v0 - data.v0/2

            newlast_outside   = numpy.zeros([diff,2]) == 1

            data.pos  = numpy.append(data.pos,  newpos,  axis=0)
            data.vel  = numpy.append(data.vel,  newvel,  axis=0)

            data.last_outside = numpy.append(data.last_outside, newlast_outside, axis=0)


    def mainloop(self):

        # set up pygame clock
        clock = pygame.time.Clock()

        while not self.data.closed:

            # limit clock rate to framerate
            clock.tick(self.data.fps)

            # test for exit request
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()

            # if the number of balls has changed then call self.n_balls to change the number of balls rendered
            if self.data.n != len(self.data.pos):

                self.n_balls()
    
            # render scene

            self.draw()
            self.gravity()
            self.bounce()
            self.collide()
            self.evolve_fade()

            #self.energy()

            # update screen 
            pygame.display.flip()

            # update panel
            self.panel.update_idletasks()
            self.panel.update()


class Data(object):

    def __init__(self):

        pass


class Panel(gooey.Tk):

    def __init__(self, parent, data):

        self.parent = parent
        self.data   = data

        gooey.Tk.__init__(self)
        self.config(padx=SP,pady=SP*0.5)
        self.resizable(0,0) # disable resizing

        self.wm_title(' Balls') # set title

        icon = tkinter.PhotoImage(file=r'assets/favicon.gif') # setting favicon
        self.tk.call('wm', 'iconphoto', self._w, icon)  

        self.closed = False
        self.fade   = True

        self.protocol("WM_DELETE_WINDOW", self.close) # call self.close() if window is closed by user

        # Creating fonts

        arial_big   = Font(family="Arial",   size=int(SP*1.2),  weight='bold')
        arial_med   = Font(family="Arial",   size=int(SP*1),   weight='bold')

        verdana_big = Font(family="Verdana", size=int(SP))
        verdana_med = Font(family="Verdana", size=int(SP//1.5), weight='bold')
        verdana_sml = Font(family="Verdana", size=int(SP//2.2), weight='bold')
        verdana_min = Font(family="Verdana", size=int(SP//2.7), weight='bold')

        # Creating widgets

        gooey.Spacer(self, width=SP).grid(row=0, column=1)

        s_frame = gooey.Frame(self)
        s_frame.grid(row=0, column=2)

        self.balls = gooey.Label(s_frame, text='Options', font=arial_big)
        self.balls.grid(sticky='w', row=0, columnspan=3)


        gooey.Spacer(s_frame,height=SP).grid(row=1)
        gooey.Spacer(s_frame,width=SP).grid(row=2, column=0)

        self.grav_title = gooey.Label(s_frame, text='Gravity', font=verdana_med, fg='grey34')
        self.grav_title.grid(row=2, column=1, sticky='w')

        gooey.Spacer(s_frame,width=SP).grid(row=2, column=2)

        self.grav_scale = gooey.Scale(s_frame, height=SP, length=SP*12, width=SP*100, from_=-0.1, to=0.1)
        self.grav_scale.grid(row=2, column=3)
        self.grav_scale.set(0.005)

        gooey.Spacer(s_frame,width=SP).grid(row=2, column=4)

        self.grav_label = gooey.Label(s_frame, text='0.005', width='6', font=verdana_sml, fg='grey34')
        self.grav_label.grid(row=2, column=5)

        gooey.Spacer(s_frame,height=SP).grid(row=3)
        gooey.Spacer(s_frame,width=SP).grid(row=4, column=0)

        self.rest_title = gooey.Label(s_frame, text='Restitution', font=verdana_med, fg='grey34')
        self.rest_title.grid(row=4, column=1, sticky='w')

        gooey.Spacer(s_frame,width=SP).grid(row=4, column=2)

        self.rest_scale = gooey.Scale(s_frame, height=SP, length=SP*12, width=SP*100, from_=0, to=1)
        self.rest_scale.grid(row=4, column=3)
        self.rest_scale.set(1)

        gooey.Spacer(s_frame,width=SP).grid(row=4, column=4)

        self.rest_label = gooey.Label(s_frame, text='1.0', font=verdana_sml, fg='grey34')
        self.rest_label.grid(row=4, column=5)


        gooey.Spacer(s_frame,height=SP).grid(row=5)
        gooey.Spacer(s_frame,width=SP).grid(row=6, column=0)

        self.radius_title = gooey.Label(s_frame, text='Ball Radius', font=verdana_med, fg='grey34')
        self.radius_title.grid(row=6, column=1, sticky='w')

        gooey.Spacer(s_frame,width=SP).grid(row=6, column=2)

        self.radius_scale = gooey.Scale(s_frame, height=SP, length=SP*12, width=SP*100, from_=2, to=SP*3, value_type='int')
        self.radius_scale.grid(row=6, column=3)
        self.radius_scale.set(SP//2)

        gooey.Spacer(s_frame,width=SP).grid(row=6, column=4)

        self.radius_label = gooey.Label(s_frame, text=str(SP//2), font=verdana_sml, fg='grey34')
        self.radius_label.grid(row=6, column=5)


        gooey.Spacer(s_frame,height=SP).grid(row=7)
        gooey.Spacer(s_frame,width=SP).grid(row=8, column=0)

        self.number_title = gooey.Label(s_frame, text='Ball Count', font=verdana_med, fg='grey34')
        self.number_title.grid(row=8, column=1, sticky='w')

        gooey.Spacer(s_frame,width=SP).grid(row=8, column=2)

        self.number_scale = gooey.Scale(s_frame, height=SP, length=SP*12, width=SP*100, from_=1, to=200, value_type='int')
        self.number_scale.grid(row=8, column=3)
        self.number_scale.set(70)

        gooey.Spacer(s_frame,width=SP).grid(row=8, column=4)

        self.number_label = gooey.Label(s_frame, text='70', font=verdana_sml, fg='grey34')
        self.number_label.grid(row=8, column=5)


        gooey.Spacer(s_frame,height=SP).grid(row=9)

        self.colour_options_title = gooey.Label(s_frame, text='Colour Options', font=arial_med, fg='black')
        self.colour_options_title.grid(row=10, column=0, columnspan=4, sticky='w')


        gooey.Spacer(s_frame,height=SP).grid(row=11)
        gooey.Spacer(s_frame,width=SP).grid(row=12, column=0)

        self.hex_title = gooey.Label(s_frame, text='Base Colour (hex)', font=verdana_sml, fg='grey34')
        self.hex_title.grid(row=12, column=1, sticky='w')

        gooey.Spacer(s_frame,width=SP).grid(row=12, column=2)

        self.hex_entry = gooey.Entry(s_frame)
        self.hex_entry.grid(row=12, column=3, sticky='nsw',ipady=4)
        self.hex_entry.insert(0,'#22eeff')

        self.fade_title = gooey.Label(s_frame, text='Fade:', font=verdana_sml, fg='grey34')
        self.fade_title.grid(row=12, column=3, sticky='e')

        self.fade_button = gooey.EdgeButton(s_frame, text='On', font=verdana_sml, fg='grey34', command= self.toggle_fade)
        self.fade_button.grid(row=12, column=5, sticky='nswe')


        gooey.Spacer(s_frame,height=SP*0.7).grid(row=13)
        gooey.Spacer(s_frame,width=SP).grid(row=14, column=0)

        self.val_v_title = gooey.Label(s_frame, text='Value Variance', font=verdana_sml, fg='grey34')
        self.val_v_title.grid(row=14, column=1, sticky='w')

        gooey.Spacer(s_frame,width=SP).grid(row=14, column=2)

        self.val_v_scale = gooey.Scale(s_frame, height=SP, length=SP*12, width=SP*100, from_=0, to=1)
        self.val_v_scale.grid(row=14, column=3)
        self.val_v_scale.set(1.0)

        gooey.Spacer(s_frame,width=SP).grid(row=14, column=4)

        self.val_v_label = gooey.Label(s_frame, text='1.0', font=verdana_min, fg='grey34')
        self.val_v_label.grid(row=14, column=5)


        gooey.Spacer(s_frame,height=SP).grid(row=15)
        gooey.Spacer(s_frame,width=SP).grid(row=16, column=0)

        self.hue_v_title = gooey.Label(s_frame, text='Hue Variance', font=verdana_sml, fg='grey34')
        self.hue_v_title.grid(row=16, column=1, sticky='w')

        gooey.Spacer(s_frame,width=SP).grid(row=16, column=2)

        self.hue_v_scale = gooey.Scale(s_frame, height=SP, length=SP*12, width=SP*100, from_=0, to=1)
        self.hue_v_scale.grid(row=16, column=3)
        self.hue_v_scale.set(0.5)

        gooey.Spacer(s_frame,width=SP).grid(row=16, column=4)

        self.hue_v_label = gooey.Label(s_frame, text='0.5', font=verdana_min, fg='grey34')
        self.hue_v_label.grid(row=16, column=5)

        gooey.Spacer(s_frame,height=SP).grid(row=17)


    def close(self):

        data = self.data

        # self.close is called when the tkinter window is closed - alerts the pygame window to close
        data.closed = True
        self.destroy()


    def get_vars(self,_):

        # for each variable, set the value in data to the right value and update the value label

        self.data.g     = self.grav_scale.get()
        self.data.rest  = self.rest_scale.get()
        self.data.r     = self.radius_scale.get()
        self.data.n     = self.number_scale.get()
        self.data.hex   = self.hex_entry.get()
        self.data.hue_v = self.hue_v_scale.get()
        self.data.val_v = self.val_v_scale.get()

        self.grav_label['text']   = str(round(self.data.g, 4))
        self.rest_label['text']   = str(round(self.data.rest, 4))
        self.radius_label['text'] = str(round(self.data.r, 4))
        self.number_label['text'] = str(round(self.data.n, 4))
        self.hue_v_label['text']  = str(round(self.data.hue_v, 4))
        self.val_v_label['text']  = str(round(self.data.val_v, 4))


    def toggle_fade(self):

        data = self.data

        # inverts value of self.fade
        data.fade = not data.fade

        # sets text on button to represent value of self.fade
        self.fade_button['text'] = 'On' if data.fade else 'Off'

Balls()