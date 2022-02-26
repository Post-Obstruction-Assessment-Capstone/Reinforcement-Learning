

import airsim
import os
import numpy as np
import pandas as pd
import time
import cv2

class Environment:
    def __init__(self, vehicle_name,  home= (0,0,0), maxz=120, maxspeed=8.33, episode_time=9): # change episode_time to 900 seconds (15 minutes)
        self.vehicle_name =vehicle_name
        self.home=home
        self.maxz=maxz
        self.maxspeed=maxspeed
        self.episode_time=episode_time
        self.reward=0


    def StartTime(self, start):
        self.start=start; self.end=start
    def GetTime(self, end): self.end=end

    def make_env(self):
         # connect to the simulator
        self.client=airsim.MultirotorClient()
        self.client.confirmConnection()
        self.client.enableApiControl(True, vehicle_name=self.vehicle_name) # enable API control on Drone0
        self.client.armDisarm(True, vehicle_name=self.vehicle_name)        # arm Drone

        self.client.takeoffAsync(vehicle_name=self.vehicle_name).join()  # let take-off
        self.client.moveToPositionAsync(self.home[0], self.home[1], self.home[2], 5, # 5m/s
                                   vehicle_name=self.vehicle_name).join()  #(note the inverted Z axis)
        print("Honey I'm home")
        self.client.hoverAsync(vehicle_name=self.vehicle_name).join()

        self.addWeather(weather=True, leaf=0.05, Roadwetness=0.1)
        time.sleep(2)

    def reset(self):
        self.client.reset()
        self.client.enableApiControl(True)
        self.client.armDisarm(True)
        self.client.takeoffAsync().join()
        # future add ignore collisions until drone is at home position
        self.client.moveToPositionAsync(self.home[0], self.home[1], self.home[2], 5,
                                   vehicle_name=self.vehicle_name).join()
        print("Honey I'm home")
        self.client.hoverAsync(vehicle_name=self.vehicle_name).join()
        time.sleep(0.5)



    def get_position(self):
        return self.client.getMultirotorState().kinematics_estimated.position
    def get_velocity(self):
        return self.client.getMultirotorState().kinematics_estimated.linear_velocity

    def step(self, action):

        # convert actions to movement
        quad_vel = self.client.getMultirotorState().kinematics_estimated.linear_velocity
        self.quad_offset = self.interpret_action(action)
        MOVEMENT_INTERVAL = 1
        self.client.moveByVelocityAsync(
            quad_vel.x_val + self.quad_offset[0],
            quad_vel.y_val + self.quad_offset[1],
            quad_vel.z_val + self.quad_offset[2],
            1 ).join()
        quad_state = self.client.getMultirotorState().kinematics_estimated.position
        #print( quad_state)
        time.sleep(0.5)
        # get images
        next_state=self.next_state()


        return 'next_state', 'reward', self.done(), 'info'


    def done(self):
        done=False
        # episode ends if time runs out or collision
        deltaTime=self.end - self.start
        timeisUp = True if deltaTime>=self.episode_time else False
        if timeisUp: print('tic toc ... time is up')
        if self.client.simGetCollisionInfo().has_collided: print('Oh fiddlesticks, we just hit something...')
        if timeisUp or self.client.simGetCollisionInfo().has_collided: done = True

        return done

    def reward(self):
        if self.client.simGetCollisionInfo().has_collided: self.reward-=1000
        # reward for finding obstruction +100
            # convert found flag to True
        # reward for road and powerline follow needed
        # Drone update to pandas?
            # Get distance between drone if less than 100 meters update dataframe
            # penalize duplicate locations
            # bonus for update with obstructions
            # Method to prevent constant updating/ reward maximization of swarm
        # penalize entering no fly zone

    def next_state(self):
        # size 224x224 images
        # get depth image
        responses = self.client.simGetImages([airsim.ImageRequest("front_center", airsim.ImageType.DepthPlanar, pixels_as_float=True),
                                              airsim.ImageRequest("front_center", airsim.ImageType.Scene, False, False),
                                              airsim.ImageRequest("bottom_center", airsim.ImageType.Scene, False, False),



        ])
        gps_data = self.client.getGpsData()
        #print(gps_data)


        for idx, response in enumerate(responses):
            filename = os.path.join('data', str(idx))
            #print(response.height, response.width)
            if idx==0:
                 filename = os.path.join('data', 'Front_center_DepthPlanar')
                 img1d = np.array(response.image_data_float, dtype=np.float)
                 img1d = img1d * 3.5 + 30
                 img1d[img1d > 255] = 255
                 depth = np.reshape(img1d, (response.height, response.width))
                 np.save(filename, depth)
            elif idx ==1:
                filename = os.path.join('data', 'Front_center_RGB')
                img1d = np.fromstring(response.image_data_uint8, dtype=np.uint8) # get numpy array
                img_rgb = img1d.reshape(3, response.height, response.width) # reshape array to 4 channel image array H X W X 3
                np.save(filename, img_rgb)

            else:
                filename = os.path.join('data', 'Bottom_center_RGB')
                img1d = np.fromstring(response.image_data_uint8, dtype=np.uint8) # get numpy array
                img_rgb = img1d.reshape(3, response.height, response.width) # reshape array to 4 channel image array H X W X 3
                np.save(filename, img_rgb)



        # previous 3 graysacle image frames
        # Depth of current frame
        # update map images
            # store positions, velocities, vehicle name, T/F Obstruction found
            # Map to have no fly zones

        # return stacked image frames to n-channel image
        return 'state_'

    def interpret_action(self, action):
        """Interprete action"""
        scale= 2
        assert action in np.arange(0,7)
        if action == 0:
            self.quad_offset = (0, 0, 0)
        elif action == 1:
            self.quad_offset = (scale, 0, 0)
        elif action == 2:
            self.quad_offset = (0, scale, 0)
        elif action == 3:
            self.quad_offset = (0, 0, scale)
        elif action == 4:
            self.quad_offset = (-scale, 0, 0)
        elif action == 5:
            self.quad_offset = (0, -scale, 0)
        elif action == 6:
            self.quad_offset = (0, 0, -scale)

        return self.quad_offset


    def addWeather(self, weather= False, fog=0.0, rain=0.0, dust=0.0, snow=0.0, leaf=0.0, Roadwetness=0.0):
        self.client.simEnableWeather(weather)
        if weather==True:
            self.client.simSetWeatherParameter(airsim.WeatherParameter.Fog, fog);
            self.client.simSetWeatherParameter(airsim.WeatherParameter.Rain, rain);
            self.client.simSetWeatherParameter(airsim.WeatherParameter.Snow, snow);
            self.client.simSetWeatherParameter(airsim.WeatherParameter.MapleLeaf, leaf);
            self.client.simSetWeatherParameter(airsim.WeatherParameter.Roadwetness, Roadwetness);
