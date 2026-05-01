import plotly.graph_objects as go
import numpy as np


# Parameters
nm_to_ft = 6076.12
ft_to_nm = 1 / nm_to_ft
R_s = 10 * nm_to_ft  # detection range (ft)
R_adv = 4 * nm_to_ft  # advisory trigger range (ft)
climb_rate = 5  # ft per timestep
escaped_adv_height = 300  # ft

# Time steps
t = np.linspace(0, 90, 800)

# Horizontal motion (closing distance)
x1 = -20 + 0.5 * t  # Aircraft A moving right
x2 = 20 - 0.5 * t  # Aircraft B moving left

# Initial altitude (same)
alt1 = np.full_like(t, 30000)
alt2 = np.full_like(t, 30000)

vec1 = np.vstack((x1 * nm_to_ft, alt1))
vec2 = np.vstack((x2 * nm_to_ft, alt2))


# Flags
detected = False
advisory = False

frames = []
num_iters_in_advisory = 0
past_advisory = False
past_detection = False
for i in range(len(t)):
    dist = np.sqrt(((vec1[:, i] - vec2[:, i]) ** 2).sum())

    # Detection condition
    if dist <= R_s:
        detected = True
    else:
        detected = False

    # Advisory condition
    if dist <= R_adv:
        advisory = True
        num_iters_in_advisory += 1
    else:
        advisory = False
    alt_sep = vec1[1, i] - vec2[1, i]
    # Apply vertical maneuver after advisory
    if advisory and not (alt_sep >= escaped_adv_height):
        add = vec1[1, i] + climb_rate * num_iters_in_advisory
        sub = vec2[1, i] - climb_rate * num_iters_in_advisory
        vec1[1, i] = add
        vec2[1, i] = sub
    adjusted_alt_sep = vec1[1, i] - vec2[1, i]

    # Annotations
    annotations = []

    annotations.append(
        dict(
            x=20,
            y=30850,
            text=(
                "<b>Parameters</b><br>"
                f"R_s = {R_s * ft_to_nm} nm<br>"
                f"R_adv = {R_adv * ft_to_nm} nm<br>"
                f"H = {escaped_adv_height} ft"
            ),
            showarrow=False,
            align="left",
            font=dict(color="black"),
            name="param_label",
            bordercolor="black",
            borderwidth=1,
        )
    )

    if detected:  # Annotation when TCAS-SURV-001 logic is activated
        annotations.append(
            dict(
                x=0,
                y=30500,
                text="Aircraft Detected",
                name="det_label",
                showarrow=False,
                bordercolor="black",
                borderwidth=0,
                font=dict(color="orange"),
            )
        )
        tcas_surv_001_t_step = i
    elif (
        past_detection
    ):  # Annotation when TCAS-TRACK-005 is activated, no longer in detection range
        tcas_track_005_t_step = i
    adjusted_dist = np.sqrt(((vec1[:, i] - vec2[:, i]) ** 2).sum())
    if adjusted_dist <= R_adv:
        annotations.append(
            dict(
                x=0,
                y=30700,
                name="ra_label",
                text="Resolution Advisory Active",
                showarrow=False,
                bordercolor="black",
                borderwidth=0,
                font=dict(color="red"),
            )
        )

    annotations.append(
        dict(
            x=20,
            y=30650,
            text=(
                "<b>Live Data</b><br>"
                f"Horizontal Dist: {adjusted_dist * ft_to_nm:.2f} nm<br>"
                f"Vertical Sep: {adjusted_alt_sep:.0f} ft"
            ),
            showarrow=False,
            name="dist_labels",
            align="left",
            bordercolor="black",
            borderwidth=1,
            font=dict(color="black"),
        )
    )

    if (adjusted_alt_sep) >= escaped_adv_height:
        if not past_advisory:  # Annontation when TCAS-ADV-005 is activated
            tcas_adv_005_t_step = i
            # latch onto last altititude bc sim is contrived to hold constant alt once clear
            vec1[1, i:] = vec1[1, i]
            vec2[1, i:] = vec2[1, i]
            past_advisory = True
        annotations.append(
            dict(
                x=0,
                y=30300,
                text="Clear of Conflict",
                showarrow=False,
                name="conflict_clear_label",
                bordercolor="black",
                borderwidth=0,
                font=dict(color="green"),
            )
        )

    frame = go.Frame(
        data=[
            go.Scatter(x=[x1[i]], y=[vec1[1, i]], mode="markers", name="Aircraft A"),
            go.Scatter(x=[x2[i]], y=[vec2[1, i]], mode="markers", name="Aircraft B"),
        ],
        layout=go.Layout(
            annotations=[]
        ),  # add as empty to reset so they dont clobber each other
    )
    frame.layout.annotations = annotations
    frames.append(frame)

fig = go.Figure(
    data=[
        go.Scatter(x=[x1[0]], y=[alt1[0]], mode="markers", name="Aircraft A"),
        go.Scatter(x=[x2[0]], y=[alt2[0]], mode="markers", name="Aircraft B"),
    ],
    layout=go.Layout(
        title="TCAS Collision Avoidance Simulation",
        xaxis=dict(title="Horizontal Distance (nm)", range=[-25, 25]),
        yaxis=dict(title="Altitude (ft)", range=[29500, 31000]),
        updatemenus=[
            dict(
                type="buttons",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[
                            None,
                            {
                                "frame": {"duration": 5, "redraw": True},
                                "transition": {"duration": 0},
                            },
                        ],
                    )
                ],
            )
        ],
    ),
    frames=frames,
)
fig.show()
