import plotly.graph_objects as go
import numpy as np

# Parameters
nm_to_ft = 6076.12
ft_to_nm = 1/nm_to_ft
R_s = 10*nm_to_ft      # detection range (ft)
R_adv = 4*nm_to_ft     # advisory trigger range (ft)
climb_rate = 5  # ft per timestep
escaped_adv_height = 300 # ft

# Time steps
t = np.linspace(0, 60, 500)

# Horizontal motion (closing distance)
x1 = -20 + 0.5 * t   # Aircraft A moving right
x2 = 20 - 0.5 * t    # Aircraft B moving left

# Initial altitude (same)
alt1 = np.full_like(t, 30000)
alt2 = np.full_like(t, 30000)

vec1 = np.vstack((x1*nm_to_ft, alt1))
vec2 = np.vstack((x2*nm_to_ft, alt2))



# Flags
detected = False
advisory = False

frames = []
num_iters_in_advisory = 0
past_advisory = False
for i in range(len(t)):
    dist = np.sqrt(((vec1[:,i] - vec2[:,i])**2).sum())

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

    # Apply vertical maneuver after advisory
    if advisory and not ((vec1[1,i] - vec2[1,i]) >= escaped_adv_height):
        add = vec1[1,i] + climb_rate * num_iters_in_advisory
        sub = vec2[1,i] - climb_rate * num_iters_in_advisory
        print(add, sub)
        vec1[1,i] = add
        vec2[1,i] = sub

    # Annotations
    annotations = []

    if detected:
        annotations.append(dict(
            x=0, y=30500,
            text="Aircraft Detected",
            showarrow=False,
            font=dict(color="orange")
        ))
    adjusted_dist = np.sqrt(((vec1[:,i] - vec2[:,i])**2).sum())
    if adjusted_dist <= R_adv:
        annotations.append(dict(
            x=0, y=30700,
            text="Resolution Advisory Active",
            showarrow=False,
            font=dict(color="red")
        ))

    if (vec1[1,i] - vec2[1,i]) >= escaped_adv_height:
        if not past_advisory:
            # latch onto last altititude bc sim is contrived to hold constant alt once clear
            vec1[1,i:] = vec1[1,i]
            vec2[1,i:] = vec2[1,i]
            past_advisory = True
        annotations.append(dict(
            x=0, y=30300,
            text="Clear of Conflict",
            showarrow=False,
            font=dict(color="green")
        ))

    frames.append(go.Frame(
        data=[
            go.Scatter(x=[x1[i]], y=[vec1[1,i]], mode="markers", name="Aircraft A"),
            go.Scatter(x=[x2[i]], y=[vec2[1,i]], mode="markers", name="Aircraft B")
        ],
        layout=go.Layout(annotations=annotations)
    ))

# Initial figure
fig = go.Figure(
    #render_mode="webgl",
    #animation_frame=t,
    data=[
        go.Scatter(x=[x1[0]], y=[alt1[0]], mode="markers", name="Aircraft A"),
        go.Scatter(x=[x2[0]], y=[alt2[0]], mode="markers", name="Aircraft B")
    ],
    layout=go.Layout(
        title="TCAS Collision Avoidance Simulation",
        xaxis=dict(title="Horizontal Distance (nm)", range=[-25, 25]),
        yaxis=dict(title="Altitude (ft)", range=[29500, 31000]),
        updatemenus=[dict(
            type="buttons",
            buttons=[dict(label="Play",
                          method="animate",
                          args=[None, {"frame": {"duration": 5, "redraw": True}, "transition": {"duration":0}}])]
        )]
    ),
    frames=frames
)

fig.write_html("index.html")
#fig.show()
