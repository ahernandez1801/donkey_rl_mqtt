# Adapted from https://github.com/sergionr2/RacingRobot
# Author: Antonin Raffin
import argparse
import os
import time
from threading import Event, Thread

import numpy as np
import pygame
from pygame.locals import *
from stable_baselines.bench import Monitor
from stable_baselines.common.vec_env import VecFrameStack, VecNormalize, DummyVecEnv


from gym_donkeycar.envs.vae_env import DonkeyVEnv





MAX_TURN = 1
# Smoothing constants
STEP_THROTTLE = 0.3
STEP_TURN = 0.4

TELEOP_RATE = 1 / 60  # 60 fps
GREEN = (72, 205, 40)
RED = (205, 39, 46)
GREY = (187, 179, 179)
BLACK = (36, 36, 36)
WHITE = (230, 230, 230)
ORANGE = (200, 110, 0)


pygame.font.init()
FONT = pygame.font.SysFont('Open Sans', 25)
SMALL_FONT = pygame.font.SysFont('Open Sans', 20)
KEY_MIN_DELAY = 0.4


def control(x, theta, control_throttle, control_steering):
    """
    Smooth control.

    :param x: (float)
    :param theta: (float)
    :param control_throttle: (float)
    :param control_steering: (float)
    :return: (float, float)
    """
    target_throttle = x
    target_steering = MAX_TURN * theta
    if target_throttle > control_throttle:
        control_throttle = min(target_throttle, control_throttle + STEP_THROTTLE)
    elif target_throttle < control_throttle:
        control_throttle = max(target_throttle, control_throttle - STEP_THROTTLE)
    else:
        control_throttle = target_throttle

    if target_steering > control_steering:
        control_steering = min(target_steering, control_steering + STEP_TURN)
    elif target_steering < control_steering:
        control_steering = max(target_steering, control_steering - STEP_TURN)
    else:
        control_steering = target_steering
    return control_throttle, control_steering


class TeleopEnv(object):
    def __init__(self,):
        super(TeleopEnv, self).__init__()
        # For display
        self.is_filling = False
        self.current_obs = None
        self.exit_event = Event()
        self.done_event = Event()
        self.ready_event = Event()

        self.start_process()

    def start_process(self):
        """Start preprocessing process"""
        self.process = Thread(target=self.main_loop)
        # Make it a deamon, so it will be deleted at the same time
        # of the main process
        self.process.daemon = True
        self.process.start()
        
    def render(self, mode='human'):
        return self.env.render(mode)

    def reset(self):
        self.n_out_of_bound = 0
        # Disable reset after init
        if self.need_reset:
            self.need_reset = False
            return self.env.reset()
        else:
            # Zero speed, neutral angle
            self.donkey_env.controller.take_action([0, 0])
            return self.current_obs

    def wait_for_teleop_reset(self):
        self.ready_event.wait()
        return self.reset()

    def exit(self):
        self.env.reset()
        self.donkey_env.exit_scene()

    def wait(self):
        self.process.join()

    def main_loop(self):
        # Pygame require a window
        pygame.init()

        self.window = pygame.display.set_mode((800, 500), RESIZABLE)

        end = False

        control_throttle, control_steering = 0, 0
        action = [control_steering, control_throttle]
        self.update_screen(action)

        donkey_env = self.env
        # Unwrap env
        if isinstance(donkey_env, Recorder):
            donkey_env = donkey_env.env
        while isinstance(donkey_env, VecNormalize) or isinstance(donkey_env, VecFrameStack):
            donkey_env = donkey_env.venv

        if isinstance(donkey_env, DummyVecEnv):
            donkey_env = donkey_env.envs[0]
        if isinstance(donkey_env, Monitor):
            donkey_env = donkey_env.env

        assert isinstance(donkey_env, DonkeyVAEEnv), print(donkey_env)
        self.donkey_env = donkey_env

        last_time_pressed = {'space': 0, 'm': 0, 't': 0, 'b': 0, 'o': 0}
        self.current_obs = self.reset()

        if self.model is not None:
            # Prevent error (uninitialized value)
            self.model.n_updates = 0

        while not end:
            x, theta = 0, 0
            keys = pygame.key.get_pressed()
            for keycode in moveBindingsGame.keys():
                if keys[keycode]:
                    x_tmp, th_tmp = moveBindingsGame[keycode]
                    x += x_tmp
                    theta += th_tmp

            if keys[K_SPACE] and (time.time() - last_time_pressed['space']) > KEY_MIN_DELAY:
                self.is_recording = not self.is_recording
                if isinstance(self.env, Recorder):
                    self.env.toggle_recording()
                # avoid multiple key press
                last_time_pressed['space'] = time.time()

            if keys[K_m] and (time.time() - last_time_pressed['m']) > KEY_MIN_DELAY:
                self.is_manual = not self.is_manual
                # avoid multiple key press
                last_time_pressed['m'] = time.time()
                if self.is_training:
                    if self.is_manual:
                        # Stop training
                        self.ready_event.clear()
                        self.done_event.set()
                    else:
                        # Start training
                        self.done_event.clear()
                        self.ready_event.set()

            if keys[K_t] and (time.time() - last_time_pressed['t']) > KEY_MIN_DELAY:
                self.is_training = not self.is_training
                # avoid multiple key press
                last_time_pressed['t'] = time.time()

            if keys[K_b] and (time.time() - last_time_pressed['b']) > KEY_MIN_DELAY:
                self.fill_buffer = not self.fill_buffer
                # avoid multiple key press
                last_time_pressed['b'] = time.time()

            if keys[K_r]:
                self.current_obs = self.env.reset()

            if keys[K_o]:
                if (self.is_manual
                        and self.model is not None
                        and hasattr(self.model, 'optimize')
                        and (time.time() - last_time_pressed['o']) > KEY_MIN_DELAY):
                    print("Optimizing")
                    self.model.optimize(len(self.model.replay_buffer), None, self.model.learning_rate(1))
                    last_time_pressed['o'] = time.time()

            if keys[K_l]:
                self.env.reset()
                self.donkey_env.exit_scene()
                self.need_reset = True

            # Smooth control for teleoperation
            control_throttle, control_steering = control(x, theta, control_throttle, control_steering)
            # Send Orders
            if self.model is None or self.is_manual:
                t = (control_steering + MAX_TURN) / (2 * MAX_TURN)
                steering_order = MIN_STEERING * t + MAX_STEERING * (1 - t)
                self.action = [steering_order, control_throttle]
            elif self.model is not None and not self.is_training:
                self.action, _ = self.model.predict(self.current_obs, deterministic=self.deterministic)

            self.is_filling = False
            if not (self.is_training and not self.is_manual):
                if self.is_manual and not self.fill_buffer:
                    donkey_env.controller.take_action(self.action)
                    self.current_obs, reward, done, info = donkey_env.observe()
                    self.current_obs, _, _, _ = donkey_env.postprocessing_step(self.action, self.current_obs,
                                                                               reward, done, info)

                else:
                    if self.fill_buffer:
                        old_obs = self.current_obs
                    self.current_obs, reward, done, _ = self.env.step(self.action)

                    # Store the transition in the replay buffer
                    if self.fill_buffer and hasattr(self.model, 'replay_buffer'):
                        assert old_obs is not None
                        if old_obs.shape[1] == self.current_obs.shape[1]:
                            self.is_filling = True
                            self.model.replay_buffer.add(old_obs, self.action, reward, self.current_obs, float(done))

            if isinstance(self.env, Recorder):
                self.env.save_image()

            self.current_image = self.env.render(mode='rgb_array')

            self.update_screen(self.action)

            for event in pygame.event.get():
                if event.type == QUIT or event.type == KEYDOWN and event.key in [K_ESCAPE, K_q]:
                    end = True
            pygame.display.flip()
            # Limit FPS
            pygame.time.Clock().tick(1 / TELEOP_RATE)
        self.ready_event.set()
        self.exit_event.set()

    def write_text(self, text, x, y, font, color=GREY):
        text = str(text)
        text = font.render(text, True, color)
        self.window.blit(text, (x, y))

    def clear(self):
        self.window.fill((0, 0, 0))

    def update_screen(self, action):
        self.clear()
        steering, throttle = action
        self.write_text('Throttle: {:.2f}, Steering: {:.2f}'.format(throttle, steering), 20, 0, FONT, WHITE)

        help_str = 'Use arrow keys to move, q or ESCAPE to exit.'
        self.write_text(help_str, 20, 50, SMALL_FONT)
        help_2 = 'space key: toggle recording -- m: change mode -- r: reset -- l: reset track'
        self.write_text(help_2, 20, 100, SMALL_FONT)

        if isinstance(self.env, Recorder):
            self.write_text('Recording Status:', 20, 150, SMALL_FONT, WHITE)
            if self.is_recording:
                text, text_color = 'RECORDING', RED
            else:
                text, text_color = 'NOT RECORDING', GREEN
            self.write_text(text, 200, 150, SMALL_FONT, text_color)

        self.write_text('Mode:', 20, 200, SMALL_FONT, WHITE)
        if self.is_manual:
            text, text_color = 'MANUAL', GREEN
        else:
            text, text_color = 'AUTONOMOUS', ORANGE
        self.write_text(text, 200, 200, SMALL_FONT, text_color)

        self.write_text('Training Status:', 20, 250, SMALL_FONT, WHITE)
        if self.is_training:
            text, text_color = 'TRAINING', RED
        else:
            text, text_color = 'TESTING', GREEN
        self.write_text(text, 200, 250, SMALL_FONT, text_color)

        if self.is_filling:
            text, text_color = 'FILLING THE BUFFER', RED
        else:
            text, text_color = '', GREEN
        self.write_text(text, 200, 300, SMALL_FONT, text_color)

        if self.current_image is not None and SHOW_IMAGES_TELEOP:
            current_image = np.swapaxes(self.current_image, 0, 1)
            if self.image_surface is None:
                self.image_surface = pygame.pixelcopy.make_surface(current_image)
            pygame.pixelcopy.array_to_surface(self.image_surface, current_image)
            self.window.blit(self.image_surface, (20, 350))

        if (self.donkey_env is not None
                and self.donkey_env.vae is not None
                and self.current_obs is not None
                and SHOW_IMAGES_TELEOP):
            vae_dim = self.donkey_env.vae.z_size
            encoded = self.current_obs[:, :vae_dim]
            reconstructed_image = self.donkey_env.vae.decode(encoded)[0]
            # Convert BGR to RGB
            # reconstructed_image = reconstructed_image[:, :, ::-1]
            reconstructed_image = np.swapaxes(reconstructed_image, 0, 1)
            if self.decoded_surface is None:
                self.decoded_surface = pygame.pixelcopy.make_surface(reconstructed_image)
            pygame.pixelcopy.array_to_surface(self.decoded_surface, reconstructed_image)
            self.window.blit(self.decoded_surface, (220, 350))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--folder', help='Log folder', type=str, default='logs')
    parser.add_argument('--record-folder', help='Record folder, where images are saved', type=str,
                        default='logs/recorded_data/')

    parser.add_argument('-n', '--n-timesteps', help='number of timesteps', default=1000,
                        type=int)
    parser.add_argument('--exp-id', help='Experiment ID (-1: no exp folder, 0: latest)', default=0,
                        type=int)
    parser.add_argument('-vae', '--vae-path', help='Path to saved VAE', type=str, default=None)
    args = parser.parse_args()

    folder = args.folder
    model = None
    vae = None
    env = TeleopEnv(env, model=model)
    
    try:
        env = TeleopEnv(env, model=model)
        env.wait()
    except KeyboardInterrupt as e:
        pass
    finally:
        env.exit()
        time.sleep(0.5)
