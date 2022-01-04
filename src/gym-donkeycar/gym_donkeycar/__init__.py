from gym.envs.registration import register
from gym_donkeycar.envs.vae_env import DonkeyVEnv

register(
    id='RealDonkey-v1',
    entry_point='gym_donkeycar.envs.gym_real:DonkeyRealEnv',
    max_episode_steps=None,
)

register(
    id='DonkeySim-v1',
    entry_point='gym_donkeycar.envs.vae_env:DonkeyVEnv',
    max_episode_steps=None,
)
