"""Shared 2D ready-stance pose for the 2D design lineup, in pixels of a 1080x1920 frame.
Hero faces right (3/4), feet on the ground line GROUND_Y, about 1000 px tall (1.75 m -> 571 px/m).
'_l' = near/lead side, '_r' = far/rear side. Scale/re-proportion as the design needs, keep the stance."""
GROUND_Y = 1560
HEAD_R = 68
POSE = dict(
    hip=(540, 1040), neck=(548, 732), head=(552, 624),
    sh_l=(560, 748), sh_r=(536, 748),
    el_l=(630, 862), ha_l=(722, 760),   # lead fist forward, up
    el_r=(505, 862), ha_r=(592, 742),   # rear fist guarding the chin
    kn_l=(650, 1290), ft_l=(700, 1555),
    kn_r=(460, 1295), ft_r=(400, 1555),
)
SEGS = [('hip', 'neck'), ('neck', 'sh_l'), ('neck', 'sh_r'), ('sh_l', 'el_l'), ('el_l', 'ha_l'), ('sh_r', 'el_r'),
        ('el_r', 'ha_r'), ('hip', 'kn_l'), ('kn_l', 'ft_l'), ('hip', 'kn_r'), ('kn_r', 'ft_r')]
