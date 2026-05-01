flowchart LR A["Nearby Aircraft Transponders"] --> B[Surveillance]

B --> C[Tracking]

C --> D["Threat
 Detection &
  Prediction"]

D -->|No Threat| E["Continue 
Monitoring"]
D -->|TA Condition| F["Traffic 
Advisory"]
D -->|RA Condition| G["Resolution 
Advisory"]

G --> H["Coordination
 with
  Intruder
   Aircraft"]

F --> I["Pilot
 
Interface"]
G --> I

I --> J["Pilot 

Action"]

H --> I

K["System
 Monitoring & 
 Control"] --> B
K --> C
K --> D
K --> G
